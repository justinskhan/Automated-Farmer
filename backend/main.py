from fastapi import FastAPI #framework to handle web server requests
from fastapi.middleware.cors import CORSMiddleware #used to allow requests from browser
from dotenv import load_dotenv #used to read the mongo db info in our hidden .env file 
from routes.auth import router as auth_router #imports our signup and login routes

load_dotenv() #loads .env file

app = FastAPI() #creates the application instance

#the following allows any domain to connect, any HTTP method as well as headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#registers the authentication routes
app.include_router(auth_router)

#make sure the server is running and show status
@app.get("/health")
def health():
    return {"status": "ok"}
