import os
import sys
import django
from transformers import pipeline
import csv
from django.utils import timezone
import random
from elasticsearch_dsl import connections, Document, Text, Date, Keyword
from fake_date import generate_fake_date_between
import psycopg2
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emotiontracking.settings')
django.setup()
from usersapp.models import CustomUser


elasticsearch_host = os.environ.get('ELASTICSEARCH_HOST', 'localhost:9200')
connections.create_connection(hosts=[elasticsearch_host])

classifier = pipeline("sentiment-analysis", model="michellejieli/emotion_text_classifier")

class NoteDocument(Document):
    text = Text()
    emotion = Keyword()
    date = Date()
    patient_username = Keyword()

    class Index:
        name = 'notes'

    def save(self, **kwargs):
        return super(NoteDocument, self).save(**kwargs)


def get_user():
    conn = psycopg2.connect(
        host='db',
        database=os.environ.get('POSTGRES_NAME'),
        user=os.environ.get('POSTGRES_USER'),
        password=os.environ.get('POSTGRES_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    query = """
        SELECT username FROM usersapp_customuser
        WHERE is_patient = true 
    """
    cursor.execute(query)
    
    user_usernames = [str(row[0]) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    if user_usernames:
        return random.choice(user_usernames)
    else:
        return None
    

def populate_index(num_texts):
    with open('data/Emotion_final.csv', 'r') as file:
        reader = csv.DictReader(file)
        rows = list(reader)  

        random_rows = random.sample(rows, num_texts)  
        for row in random_rows:
            text = row['Text']
            emotion = classifier(text)[0]['label']

            user_username = get_user()
            user = CustomUser.objects.get(username=user_username)
            date_of_registration = user.date_of_registration

            today = timezone.now().date()
            fake_date = generate_fake_date_between(date_of_registration, today)

            note = NoteDocument(text=text, emotion=emotion, date=fake_date, patient_username=user_username)
            note.save()

populate_index(500)