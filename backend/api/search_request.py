from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, root_dir)
# print(root_dir)

from search_query_handler import SearchRequest

router = APIRouter()

class SearchRequestModel(BaseModel):
    email: str
    topics: List[str]
    query_content: str
    push_time: str

@router.post("/search-request")
async def create_search_request(request: SearchRequestModel):
    try:
        # 将topics列表转换为categories字典
        categories = {"topics": request.topics}
        
        # 添加错误处理和日志
        # print(f"Processing request for email: {request.email}")
        # print(f"Topics: {request.topics}")
        # print(f"Query content: {request.query_content}")
        # print(f"Push time: {request.push_time}")
        search_request_handler = SearchRequest()
        request_id = search_request_handler.store_search_request(
            email=request.email,
            query_content=request.query_content,
            categories=categories,
            push_time=request.push_time
        )
        
        return {
            "status": "success",
            "request_id": request_id,
        }
    except Exception as e:
        print(f"Error processing request: {str(e)}")  # 添加错误日志
        raise HTTPException(
            status_code=400, 
            detail=f"Database error: {str(e)}"
        ) 