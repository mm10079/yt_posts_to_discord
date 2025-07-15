from openai import OpenAI


class Chatgpt:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def translate(self, content: str) -> str:
        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            input="請翻譯成繁體中文，保持原有文章格式，不要回覆翻譯以外的內容：\n"+content
        )
        return response.output_text

