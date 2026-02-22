from app.api.rag_router import QueryReq, rag_query

def query(query: str):
    request = QueryReq(question=query)
    response = rag_query(request)
    return response

if __name__ == "__main__":
    query("what can you do?")
