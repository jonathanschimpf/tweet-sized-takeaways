# SETUP VIRTUAL ENVIRONMENTS
python3 -m venv venv
source venv/bin/activate

# INSTALL back-end DEPENDENCIES
pip install -r back-end/requirements.txt

# RUN FastAPI FROM INSIDE back-end
cd back-end
uvicorn main:app --reload

