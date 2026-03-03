from langchain_ollama.llms import OllamaLLM
from langchain_ollama import OllamaLLM
from prompts import ROUTER_PROMPT, HR_RESPONSE_PROMPT, INJECTION_RESPONSE_PROMPT, UNKNOWN_RESPONSE_PROMPT

class SecurityFirewall:
    def __init__(self, base_url):
        # Fast model for routing
        self.router_llm = OllamaLLM(model='llama3.2:1b', base_url=base_url, num_predict=5)
        # Smart model for generating human-like refusals
        self.chat_llm = OllamaLLM(model="llama3.2:1b", base_url=base_url)
        # self.chat_llm = OllamaLLM(model="llama3.1", base_url=base_url)
    
    def process(self, user_input):
        
        """
        Classifies intent.
        Returns a tuple: (status, message)
        Status: 'SAFE' or 'BLOCKED'
        Message: If BLOCKED, this contains the human-like refusal text.
        """
        try:
            # 1. Classify
            chain = ROUTER_PROMPT | self.router_llm
            result = chain.invoke({"question": user_input})
            tag = result.strip().upper()

            # 2. Handle Blocked Requests with Human-like Responses
            if "[HR]" in tag:
                # Generate dynamic empathetic response
                refusal = self.chat_llm.invoke(HR_RESPONSE_PROMPT.format(question=user_input))
                return ("BLOCKED", refusal)

            if "[INJECTION]" in tag:
                # Generate dynamic security alert
                refusal = self.chat_llm.invoke(INJECTION_RESPONSE_PROMPT.format(question=user_input))
                return ("BLOCKED", refusal)

            if "[UNKNOWN]" in tag:
                # Generate dynamic redirect
                refusal = self.chat_llm.invoke(UNKNOWN_RESPONSE_PROMPT.format(question=user_input))
                return ("BLOCKED", refusal)

            # 3. If Safe, return SAFE status
            return ("SAFE", None)

        except Exception as e:
            print(f"Security Error: {e}")
            return ("BLOCKED", "I encountered an error processing your request.")