from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.search_request import router as search_router
from api.fetch_recent_articles import router as papers_router
from api.send_email import router as send_email_router
import uvicorn

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://arxiv.club", "http://www.arxiv.club"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)
app.include_router(papers_router)
app.include_router(send_email_router)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)