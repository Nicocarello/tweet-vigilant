from apify_client import ApifyClient
import pandas as pd
import os
from datetime import date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Reemplaza 'YOUR_API_TOKEN' con tu token API real de Apify
apify_client = ApifyClient("APIFY_API")
actor_id = "ACTOR_ID" # Puedes cambiar esto por el ID de tu Actor

SMTP_SERVER = "SMTP_SERVER"   # o smtp.office365.com para Outlook
SMTP_PORT = SMTP_PORT
FROM_EMAIL = "FROM_EMAIL"
PASSWORD = "PASSWORD"
TO_EMAILS_MELI = [TO_EMAILS_MELI]  # lista de destinatarios
TO_EMAILS_MP = [TO_EMAILS_MP]  # lista de destinatarios
TO_EMAILS_GALPERIN = [TO_EMAILS_GALPERIN]  # lista de destinatarios

# Obtener la fecha de hoy y formatearla
fecha_desde = date.today().strftime("%Y-%m-%d")

# AQUÍ EL CAMBIO: Agrupamos todos los términos con OR
# Nota: "mercadolibre" y "mercado libre" son búsquedas distintas.
frase_busqueda = '("mercado libre" OR "mercado pago" OR "mercadolibre" OR "mercadopago" OR "galperin")'

# (Aquí va tu lista_usuarios completa de 240)
lista_usuarios = [USUARIOS]

# Genera la lista searchTerms usando la fecha y la nueva frase de búsqueda
terminos_de_busqueda = [
    f"since:{fecha_desde} from:{usuario} {frase_busqueda}" for usuario in lista_usuarios
]
run_input = {
    "-min_faves": 0,
    "-min_replies": 0,
    "-min_retweets": 0,
    "filter:blue_verified": False,
    "filter:consumer_video": False,
    "filter:has_engagement": False,
    "filter:hashtags": False,
    "filter:images": False,
    "filter:links": False,
    "filter:media": False,
    "filter:mentions": False,
    "filter:native_video": False,
    "filter:nativeretweets": False,
    "filter:news": False,
    "filter:pro_video": False,
    "filter:quote": False,
    "filter:replies": False,
    "filter:safe": False,
    "filter:spaces": False,
    "filter:twimg": False,
    "filter:videos": False,
    "filter:vine": False,
    "include:nativeretweets": False,
    "maxItems": 1000000,
    "min_faves": 0,
    "min_replies": 0,
    "min_retweets": 0,
    "queryType": "Top",
    "searchTerms": terminos_de_busqueda
}

print(f"Ejecutando Actor: {actor_id}...")
run = apify_client.actor(actor_id).call(run_input=run_input)

print(f"Actor {actor_id} ejecutado. ID de la ejecución: {run['id']}")
print(f"Estado de la ejecución: {run['status']}")

# Obtener los items del dataset
dataset_items = apify_client.run(run['id']).dataset().list_items().items

# Crear el DataFrame
if dataset_items:
    df = pd.DataFrame(dataset_items)
    print("\nDataFrame creado exitosamente:")
else:
    print("\nNo se encontraron resultados en el dataset.")

# drop rows that in 'type' column contain 'mock_tweet'
df = df[df['type'] != 'mock_tweet']
df.drop_duplicates(subset='url', inplace=True)

df['userName'] = df['author'].apply(lambda author: author['userName'] if isinstance(author, dict) and 'userName' in author else None)
df['followers'] = df['author'].apply(lambda author: author['followers'] if isinstance(author, dict) and 'followers' in author else None)
df['profilePicture'] = df['author'].apply(lambda author: author['profilePicture'] if isinstance(author, dict) and 'profilePicture' in author else None)

#change format of createdAt from 0    Thu Nov 06 12:55:35 +0000 2025 to yyyy-mm-dd HH:MM:SS
df['createdAt'] = pd.to_datetime(df['createdAt'], format='%a %b %d %H:%M:%S %z %Y').dt.strftime('%Y-%m-%d %H:%M:%S')

df['interacciones'] = df['likeCount'] + df['retweetCount'] + df['replyCount'] + df['quoteCount'] + df['bookmarkCount']
df['compartidos'] = df['retweetCount'] + df['quoteCount']

desired_columns = ['userName','followers','text', 'createdAt','url', 'likeCount', 'retweetCount', 'replyCount', 'quoteCount','bookmarkCount', 'viewCount','interacciones','compartidos','profilePicture']
df = df[desired_columns]

#new column 'mencion' if 'text' contains galperin, return Galperin if contains "mercado libre" return Mercado Libre, if contains "mercadolibre" return Mercadolibre, if contains "mercado pago" return Mercado Pago, if contains "mercadopago" return Mercadopago, else None
def detectar_mencion(text):
    text_lower = text.lower()
    if "galperin" in text_lower:
        return "Galperin"
    elif "mercado libre" in text_lower:
        return "Mercado Libre"
    elif "mercadolibre" in text_lower:
        return "Mercadolibre"
    elif "mercado pago" in text_lower:
        return "Mercado Pago"
    elif "mercadopago" in text_lower:
        return "Mercadopago"
    else:
        return None

df['mencion'] = df['text'].apply(detectar_mencion)

#sort df by 'viewCount' descending
df = df.sort_values(by='viewCount', ascending=False)

df['likeCount'] = df['likeCount'].astype(int)
df['retweetCount'] = df['retweetCount'].astype(int)
df['replyCount'] = df['replyCount'].astype(int)
df['bookmarkCount'] = df['bookmarkCount'].astype(int)
df['interacciones'] = df['interacciones'].astype(int)
df['viewCount'] = df['viewCount'].astype(int)
df['compartidos'] = df['compartidos'].astype(int)
df['quoteCount'] = df['quoteCount'].astype(int)

if len(df) > 0:
    asunto = "🚨Alerta Mención Personalidad Relevante🚨"

    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    total_tweets = len(df)
    total_impresiones = int(df["viewCount"].sum())
    total_interacciones = int(df["interacciones"].sum())    

    # Encabezado y apertura del contenedor
    cuerpo_html = f"""
        <div style="font-family:Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
        <div style="max-width:700px; margin:auto; background-color:#ffffff; border-radius:12px; overflow:hidden;
                    box-shadow:0 4px 8px rgba(0,0,0,0.05);">
            
            <!-- Header -->
            <div style="background-color:#ffe600; padding:20px 30px; text-align:center;">
            <h2 style="margin:0; color:#222; font-size:20px;">🚨 Alerta de menciones - Personalidades</h2>
            <p style="margin:5px 0 0 0; color:#444; font-size:14px;">
                Menciones a <b>Mercado Libre / Mercado Pago / Galperin</b>
            </p>
            <p style="margin:5px 0 0 0; font-size:12px; color:#666;">{fecha_hoy}</p>

            <div style="margin-top:10px; background-color:#fff9c4; border-radius:8px; 
                        display:inline-block; padding:8px 15px; font-size:13px; color:#333;">
                <b>{total_tweets}</b> tweets &nbsp;•&nbsp;
                <b>{total_impresiones:,}</b> impresiones &nbsp;•&nbsp;
                <b>{total_interacciones:,}</b> interacciones
            </div>
            </div>

            <!-- Contenido -->
            <div style="padding:20px 25px;">
        """

    # Construcción de cards individuales
    for _, row in df.iterrows():
        texto = row['text'].lower()

        # Detectar mención
        if "mercado libre" in texto:
            mencion = "Mercado Libre"
        elif "mercadolibre" in texto:
            mencion = "MercadoLibre"
        elif "mercado pago" in texto:
            mencion = "Mercado Pago"
        elif "mercadopago" in texto:
            mencion = "MercadoPago"
        elif "galperin" in texto:
            mencion = "Galperin"
        else:
            mencion = "—"

        # Imagen de perfil
        profile_img_html = ""
        if row.get("profilePicture"):
            profile_img_html = f'''
            <img src="{row["profilePicture"]}" alt="Foto de perfil" width="55" height="55"
                style="border-radius:50%; margin-right:12px; border:2px solid #eee;">
            '''

        # Card
        cuerpo_html += f"""
        <div style="background-color:#fafafa; border:1px solid #e0e0e0; border-radius:10px;
                    padding:15px 20px; margin-bottom:15px; box-shadow:0 2px 5px rgba(0,0,0,0.03);">
            <div style="display:flex; align-items:center;">
            {profile_img_html}
            <div>
                <span style="font-weight:bold; font-size:15px; color:#222;">{row['userName']}</span><br>
                <span style="color:#666;">mencionó a <b>{mencion}</b></span>
            </div>
            </div>
            <p style="margin:10px 0 5px 0; color:#333; font-size:14px; line-height:1.4;">{row['text']}</p>
            <a href="{row['url']}" style="color:#0066cc; text-decoration:none; font-size:13px;">🔗 Ver tweet</a>
            <div style="margin-top:10px; border-top:1px solid #eee; padding-top:8px; font-size:13px; color:#555;">
            <b>👁️ Impresiones:</b> {row['viewCount']} &nbsp;•&nbsp;
            <b>❤️ Likes:</b> {row['likeCount']} &nbsp;•&nbsp;
            <b>💬 Comentarios:</b> {row['replyCount']} &nbsp;•&nbsp;
            <b>🔁 RT/Citas:</b> {row['compartidos']} &nbsp;•&nbsp;
            <b>🔖 Guardados:</b> {row['bookmarkCount']} &nbsp;•&nbsp;
            <b>✨ Interacciones:</b> {row['interacciones']}
            </div>
        </div>
        """

    # Pie de página
    cuerpo_html += """
        </div>
        
        <!-- Footer -->
        <div style="background-color:#f0f0f0; text-align:center; padding:15px; font-size:12px; color:#666;">
        Reporte generado automáticamente por <b>PÚBLiCA Latam</b> — Área de Data.<br>
        No responder a este correo.
        </div>
    </div>
    </div>
    """
       


    # Armar mensaje único
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(TO_EMAILS_MELI)
    msg.attach(MIMEText(cuerpo_html, "html"))

    # Enviar correo único
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(FROM_EMAIL, PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAILS_MELI, msg.as_string())

    print(f"✅ Alerta consolidada enviada con {len(df)} menciones.")
else:
    print("No se encontraron menciones relevantes hoy.")
