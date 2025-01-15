FROM joshxt/aicontainer:main
WORKDIR /
COPY docker-requirements.txt .
RUN pip install -r docker-requirements.txt
COPY . .
WORKDIR /agixt
# RUN python /agixt/Transcription.py
EXPOSE 7437
ENTRYPOINT ["python3", "DB.py"]
