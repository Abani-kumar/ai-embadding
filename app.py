import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain.document_loaders import CSVLoader
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the FastAPI app
app = FastAPI()

# 1. Vectorize the sales response CSV data
try:
    loader = CSVLoader(file_path="salaries.csv")
    documents = loader.load()
except Exception as e:
    raise RuntimeError(f"Error loading CSV file: {e}")

try:
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(documents, embeddings)
except Exception as e:
    raise RuntimeError(f"Error creating FAISS database: {e}")

# 2. Function for similarity search
def retrieve_info(query):
    try:
        similar_response = db.similarity_search(query, k=3)
        page_contents_array = [doc.page_content for doc in similar_response]
        return page_contents_array
    except Exception as e:
        raise RuntimeError(f"Error during similarity search: {e}")

# 3. Setup LLMChain & prompts
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k-0613")

template = """
You are a world-class business development representative. 
I will share a prospect's message with you and you will give me the best answer that 
I should send to this prospect based on past best practices, 
and you will follow ALL of the rules below:

1/ Response should be very similar or even identical to the past best practices, 
in terms of length, tone of voice, logical arguments and other details

2/ If the best practice is irrelevant, then try to mimic the style of the best practice to prospect's message

Below is a message I received from the prospect:
{message}

Here is a list of best practices of how we normally respond to prospects in similar scenarios:
{best_practice}

Please write the best response that I should send to this prospect:
"""

prompt = PromptTemplate(input_variables=["message", "best_practice"], template=template)
chain = LLMChain(llm=llm, prompt=prompt)

# 4. Retrieval augmented generation
def generate_response(message):
    try:
        best_practice = retrieve_info(message)
        response = chain.run(message=message, best_practice=best_practice)
        return response
    except Exception as e:
        raise RuntimeError(f"Error generating response: {e}")

# 5. Create FastAPI endpoints
class MessageRequest(BaseModel):
    message: str

@app.post("/generate-response/")
async def get_response(request: MessageRequest):
    try:
        response = generate_response(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
