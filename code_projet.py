import praw
from datetime import datetime, timedelta, timezone
import google.generativeai as genai

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



def generer_prompt_pour_gemini(mot_cle, limite=20):
    avis = chercher_avis(mot_cle, limite)

    def formatter_posts(posts):
        return "\n".join([f"- {post['titre']}" for post in posts]) or "Aucun commentaire."

    prompt = f"""
Analyse l'évolution des sentiments parmi les commentaires suivants, organisés par période. 
Indique si les sentiments deviennent plus positifs, plus négatifs ou restent stables, 
et justifie ton analyse avec des observations. Résume par une tendance globale.

📆 Il y a moins de 24h :
{formatter_posts(avis['il_y_a_24h'])}

📆 Il y a moins d'une semaine :
{formatter_posts(avis['il_y_a_une_semaine'])}

📆 Il y a moins d'un mois :
{formatter_posts(avis['il_y_a_un_mois'])}
"""
    return prompt


response = gemini_model.generate_content(generer_prompt_pour_gemini("Trump"))
print(response.text)



