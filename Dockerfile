FROM python:3
COPY requirements.txt /
WORKDIR /yatube
COPY . .
RUN pip install -r /requirements.txt
CMD python manage.py runserver 0.0.0.0:8001
EXPOSE 8001