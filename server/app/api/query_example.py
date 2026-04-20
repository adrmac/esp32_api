from app.api.rag_router import QueryReq, query

def query_example(question: str):
    request = QueryReq(question=question)
    response = query(request)
    return response

if __name__ == "__main__":
    query_example("what can you do?")
