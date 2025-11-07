from apify_client import ApifyClient
import pandas as pd
import numpy as np
import os
import sys
import time
import traceback
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# --- CARGA DE VARIABLES DE ENTORNO ---
load_dotenv()

APIFY_API = os.getenv("APIFY_API")
ACTOR_ID = os.getenv("ACTOR_ID")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
FROM_EMAIL = os.getenv("FROM_EMAIL")
PASSWORD = os.getenv("PASSWORD")

TO_EMAILS_MELI = [e.strip() for e in os.getenv("TO_EMAILS_MELI", "").split(",") if e.strip()]
TO_EMAILS_MP = [e.strip() for e in os.getenv("TO_EMAILS_MP", "").split(",") if e.strip()]
TO_EMAILS_GALPERIN = [e.strip() for e in os.getenv("TO_EMAILS_GALPERIN", "").split(",") if e.strip()]

client = ApifyClient(APIFY_API)


# --- UTILIDADES DE LOGGING ---
def log(msg: str):
    """Imprime mensajes con timestamp para mejor trazabilidad."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# --- EJECUCIÓN DE ACTOR EN APIFY ---
def ejecutar_actor(lista_usuarios, max_reintentos=3):
    fecha_desde = date.today().strftime("%Y-%m-%d")
    frase_busqueda = '("mercado libre" OR "mercado pago" OR "mercadolibre" OR "mercadopago" OR "galperin")'
    terminos = [f"since:{fecha_desde} from:{u} {frase_busqueda}" for u in lista_usuarios]
    run_input = {"maxItems": 1_000_000, "queryType": "Top", "searchTerms": terminos}

    for intento in range(1, max_reintentos + 1):
        try:
            log(f"▶ Ejecutando actor {ACTOR_ID} (intento {intento})...")
            run = client.actor(ACTOR_ID).call(run_input=run_input)
            log(f"✅ Actor ejecutado. ID: {run['id']}")
            return run
        except Exception as e:
            log(f"⚠️ Error al ejecutar actor (intento {intento}): {e}")
            if intento < max_reintentos:
                time.sleep(5 * intento)
            else:
                log("❌ Error persistente ejecutando actor.")
                traceback.print_exc()
                sys.exit(1)


# --- PROCESAMIENTO DE DATASET ---
def procesar_dataset(run_id):
    """Descarga, limpia y estructura los datos del dataset."""
    try:
        items = client.run(run_id).dataset().list_items().items
        if not items:
            return pd.DataFrame()

        df = pd.DataFrame(items)
        df = df[df['type'] != 'mock_tweet'].drop_duplicates(subset='url')

        # Expande los datos del autor (más rápido que apply)
        df_author = pd.json_normalize(df['author'])
        df = pd.concat([df, df_author[['userName', 'followers', 'profilePicture']]], axis=1)

        df['createdAt'] = pd.to_datetime(df['createdAt'], format='%a %b %d %H:%M:%S %z %Y', errors='coerce')
        df['createdAt'] = df['createdAt'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Interacciones
        df['interacciones'] = df[['likeCount', 'retweetCount', 'replyCount', 'quoteCount', 'bookmarkCount']].sum(axis=1)
        df['compartidos'] = df['retweetCount'] + df['quoteCount']

        # Detección de menciones (unificadas)
        condiciones = [
            df['text'].str.contains('galperin', case=False, na=False),
            df['text'].str.contains('mercado libre|mercadolibre', case=False, na=False),
            df['text'].str.contains('mercado pago|mercadopago', case=False, na=False),
        ]
        valores = ["Galperin", "Mercado Libre", "Mercado Pago"]
        df['mencion'] = np.select(condiciones, valores, default=None)


        columnas = [
            'userName', 'followers', 'text', 'createdAt', 'url', 'likeCount',
            'retweetCount', 'replyCount', 'quoteCount', 'bookmarkCount',
            'viewCount', 'interacciones', 'compartidos', 'profilePicture', 'mencion'
        ]
        df = df[columnas].sort_values(by='viewCount', ascending=False).reset_index(drop=True)
        return df

    except Exception as e:
        log(f"❌ Error procesando dataset: {e}")
        traceback.print_exc()
        return pd.DataFrame()


# --- GENERACIÓN DE HTML ---
def generar_html(df, mencion_filtrada: str = None):
    """Crea el HTML del mail. Si se pasa mencion_filtrada, la muestra en el header."""
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    total_tweets = len(df)
    total_impresiones = int(df["viewCount"].sum())
    total_interacciones = int(df["interacciones"].sum())

    mention_title = f" - {mencion_filtrada}" if mencion_filtrada else ""
    header = f"""
    <div style="font-family:Arial,sans-serif;background-color:#f4f6f8;padding:20px;">
      <div style="max-width:700px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 8px rgba(0,0,0,0.05);">
        <div style="background-color:#ffe600;padding:20px;text-align:center;">
          <h2>🚨 Alerta de menciones{mention_title}</h2>
          <p>Menciones a <b>Mercado Libre / Mercado Pago / Galperin</b></p>
          <p style="font-size:12px;color:#666;">{fecha_hoy}</p>
          <div style="margin-top:10px;background:#fff9c4;border-radius:8px;padding:8px 15px;display:inline-block;">
            <b>{total_tweets}</b> tweets • <b>{total_impresiones:,}</b> impresiones • <b>{total_interacciones:,}</b> interacciones
          </div>
        </div>
        <div style="padding:20px;">
    """
    # (el resto del body queda igual — no hace falta tocarlo)
    cards = []
    for _, row in df.iterrows():
        img_html = (
            f'<img src="{row["profilePicture"]}" width="55" height="55" '
            f'style="border-radius:50%;margin-right:12px;border:2px solid #eee;">'
            if row["profilePicture"] else ""
        )
        card = f"""
        <div style="background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;padding:15px 20px;margin-bottom:15px;">
            <div style="display:flex;align-items:center;">{img_html}
                <div><b>{row['userName']}</b><br><span>mencionó a <b>{row['mencion']}</b></span></div>
            </div>
            <p style="margin:10px 0;">{row['text']}</p>
            <a href="{row['url']}">🔗 Ver tweet</a>
            <div style="font-size:13px;color:#555;margin-top:10px;border-top:1px solid #eee;padding-top:8px;">
              👁️ {row['viewCount']} • ❤️ {row['likeCount']} • 💬 {row['replyCount']} • 🔁 {row['compartidos']} • ✨ {row['interacciones']}
            </div>
        </div>
        """
        cards.append(card)

    footer = """
        </div>
        <div style="background:#f0f0f0;text-align:center;padding:15px;font-size:12px;color:#666;">
          Reporte generado automáticamente por <b>PÚBLiCA Latam</b> — Área de Data.
        </div>
      </div>
    </div>
    """
    return header + "".join(cards) + footer


# --- ENVÍO DE EMAIL ---
def enviar_email(cuerpo_html, destinatarios, asunto):
    """Envía el correo HTML."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, PASSWORD)
            server.sendmail(FROM_EMAIL, destinatarios, msg.as_string())
        log(f"✅ Correo enviado a {len(destinatarios)} destinatarios.")
    except Exception as e:
        log(f"❌ Error enviando correo: {e}")
        traceback.print_exc()
        sys.exit(1)


# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    log("🚀 Iniciando alerta de menciones.")

    lista_usuarios = [u.strip() for u in os.getenv("USUARIOS", "").split(",") if u.strip()]
    if not lista_usuarios:
        log("⚠️ No se definieron usuarios en USUARIOS.")
        sys.exit(1)

    run = ejecutar_actor(lista_usuarios)
    if not run:
        log("❌ Falló la ejecución del actor.")
        sys.exit(1)

    df = procesar_dataset(run["id"])
    if df.empty:
        log("No se encontraron menciones relevantes hoy.")
        sys.exit(0)

    # --- ENVÍO POR MENCIONES (se envía un correo por cada mención relevante) ---
    menciones_y_destinatarios = {
        "Mercado Libre": TO_EMAILS_MELI,
        "Mercado Pago": TO_EMAILS_MP,
        "Galperin": TO_EMAILS_GALPERIN,
    }
    
    for mencion_nombre, destinatarios in menciones_y_destinatarios.items():
        df_m = df[df['mencion'] == mencion_nombre]
        if df_m.empty:
            log(f"ℹ️ No hay menciones para '{mencion_nombre}'. No se envía correo.")
            continue
    
        if not destinatarios:
            log(f"⚠️ No hay destinatarios configurados para '{mencion_nombre}'. Saltando envío.")
            continue
    
        # Calcular hash por grupo para evitar reenvíos duplicados
        hash_actual = hash(df_m.to_json())
        safe_name = mencion_nombre.replace(" ", "_")
        hash_file = f"last_hash_{safe_name}.txt"
    
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                last_hash = f.read().strip()
            if last_hash == str(hash_actual):
                log(f"🔁 Sin cambios en '{mencion_nombre}' desde la última ejecución. No se envía correo.")
                continue
    
        # Guardar nuevo hash
        with open(hash_file, "w") as f:
            f.write(str(hash_actual))
    
        # Generar y enviar correo
        cuerpo_html = generar_html(df_m, mencion_filtrada=mencion_nombre)
        asunto = f"🚨 Alerta Mención — {mencion_nombre} 🚨"
        try:
            enviar_email(cuerpo_html, destinatarios, asunto)
            log(f"✅ Enviado correo para '{mencion_nombre}' a {len(destinatarios)} destinatarios.")
        except Exception as e:
            log(f"❌ Error enviando correo para '{mencion_nombre}': {e}")

