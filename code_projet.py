import praw
from datetime import datetime, timedelta, timezone
import google.generativeai as genai
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
import plotly.graph_objects as go
from textblob import TextBlob

genai.configure(api_key="METTRE LE TIEN")

# Initialisation du modèle Gemini
gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest")


reddit = praw.Reddit(
    client_id='METTRE LE TIEN',              
    client_secret='METTRE LE TIEN',       
    user_agent='METTRE LE TIEN',
    username='METTRE LE TIEN',
    password='METTRE LE TIEN'
)

subreddit = reddit.subreddit('python')




def chercher_avis(mot_cle, limite=1000):
    maintenant = datetime.now(timezone.utc)
    posts_24h, posts_1w, posts_1m = [], [], []

    # D'abord, les tout récents (moins de 24h)
    for post in reddit.subreddit("all").search(mot_cle, sort='new', time_filter='day', limit=int(limite / 3)):
        date_post = datetime.fromtimestamp(post.created_utc, timezone.utc)
        age = maintenant - date_post

        info = {
            'titre': post.title,
            'url': post.url,
            'score': post.score,
            'date': date_post.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if age <= timedelta(days=1):
            posts_24h.append(info)

    # Ensuite, les posts plus anciens (jusqu’à un mois)
    for post in reddit.subreddit("all").search(mot_cle, sort='relevance', time_filter='month', limit=int(limite * 2 / 3)):
        date_post = datetime.fromtimestamp(post.created_utc, timezone.utc)
        age = maintenant - date_post

        info = {
            'titre': post.title,
            'url': post.url,
            'score': post.score,
            'date': date_post.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if timedelta(days=1) < age <= timedelta(days=7):
            posts_1w.append(info)
        elif timedelta(days=7) < age <= timedelta(days=30):
            posts_1m.append(info)

    return {
        "il_y_a_24h": posts_24h,
        "il_y_a_une_semaine": posts_1w,
        "il_y_a_un_mois": posts_1m
    }



def generer_prompt_pour_gemini(mot_cle, limite=1000):
    avis = chercher_avis(mot_cle, limite)

    def formatter_posts(posts):
        return "\n".join([f"- {post['titre']}" for post in posts]) or "Aucun commentaire."

    prompt = f"""
Analyse l'évolution des sentiments parmi les commentaires suivants, organisés par période. 
Indique si les sentiments deviennent plus positifs, plus négatifs ou restent stables, 
et justifie ton analyse avec des observations. Résume par une tendance globale.

Il y a moins de 24h :
{formatter_posts(avis['il_y_a_24h'])}

Il y a moins d'une semaine :
{formatter_posts(avis['il_y_a_une_semaine'])}

Il y a moins d'un mois :
{formatter_posts(avis['il_y_a_un_mois'])}
"""


    # Fusion de tous les avis
    tous_les_avis = avis['il_y_a_24h'] + avis['il_y_a_une_semaine'] + avis['il_y_a_un_mois']

    # A. Analyse des sentiments
    sentiments = []
    times = []

    for avis_item in tous_les_avis:
        texte = avis_item.get("titre", "")
        date = avis_item.get("date")
        if texte.strip():
            polarite = TextBlob(texte).sentiment.polarity
            sentiment = "positif" if polarite > 0 else "negatif" if polarite < 0 else "neutre"
            sentiments.append(sentiment)
            times.append(date if isinstance(date, datetime) else datetime.now())
            print(f" {texte}  Polarité : {polarite}  {sentiment}")

    # B. Statistiques
    df = Counter(sentiments)
    total = sum(df.values())
    pos_ratio = df["positif"] / total if total else 0
    neg_ratio = df["negatif"] / total if total else 0
    neu_ratio = df["neutre"] / total if total else 0

    print(f"{df['positif']}/{total} avis positifs ({pos_ratio*100:.1f}%)")
    print(f"{df['negatif']}/{total} avis négatifs ({neg_ratio*100:.1f}%)")
    print(f"{df['neutre']}/{total} avis neutres ({neu_ratio*100:.1f}%)")

    # Pourcentages
    pos_pct = pos_ratio * 100
    neg_pct = neg_ratio * 100
    neu_pct = neu_ratio * 100

    # C. Affichage avec jauge et annotations
    fig2 = go.Figure(go.Indicator(
        mode="gauge+number",
        title={"text": f"Répartition des avis sur '{mot_cle}'"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, pos_pct], "color": "green"},
                {"range": [pos_pct, pos_pct + neg_pct], "color": "gray"},
                {"range": [pos_pct + neg_pct, 100], "color": "red"}
            ]
        }
    ))

    # Ajout des annotations (trick : les positions x sont approximées visuellement)
    fig2.update_layout(
        annotations=[
            dict(x=0.15, y=0.15, text=f"Positif {pos_pct:.1f}%", showarrow=False, font=dict(color="black", size=14)),
            dict(x=0.50, y=0.15, text=f"Neutre {neu_pct:.1f}%", showarrow=False, font=dict(color="black", size=14)),
            dict(x=0.85, y=0.15, text=f"Négatif {neg_pct:.1f}%", showarrow=False, font=dict(color="black", size=14))
        ]
    )

    fig2.show()

    return prompt

response = gemini_model.generate_content(generer_prompt_pour_gemini("Musk"))
print(response.text)

print(response.text)



