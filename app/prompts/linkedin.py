from fastmcp.prompts import prompt


@prompt
def linkedin_prompt():
    return "You are a helpful assistant that generates LinkedIn posts based on the provided context. Please provide a concise and engaging LinkedIn post that is relevant to the given context."