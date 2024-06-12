import tiktoken
from collections.abc import Mapping

#Values from https://platform.openai.com/docs/models/gpt-3-5

MODELS_2_TOKEN_LIMITS = {
    "gpt-35-turbo": 4097,
    "gpt-3.5-turbo": 4097,
    "gpt-35-turbo-16k": 16385,
    "gpt-3.5-turbo-16k": 16385,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4o": 128000
}

AOAI_2_OAI = {
    "gpt-35-turbo": "gpt-3.5-turbo",
    "gpt-35-turbo-16k": "gpt-3.5-turbo-16k",
    "gpt-4o": "gpt-4o"
}


def get_token_limit(model_id: str) -> int:
    if model_id not in MODELS_2_TOKEN_LIMITS:
        raise ValueError("Expected model gpt-35-turbo and above. Got: " + model_id)
    return MODELS_2_TOKEN_LIMITS.get(model_id)


def num_tokens_from_messages(message: dict[str, str], model: str) -> int:
    """
    Calculate the number of tokens required to encode a message.
    Args:
        message (dict): The message to encode, represented as a dictionary.
        model (str): The name of the model to use for encoding.
    Returns:
        int: The total number of tokens required to encode the message.
    Example:
        message = {'role': 'user', 'content': 'Hello, how are you?'}
        model = 'gpt-3.5-turbo'
        num_tokens_from_messages(message, model)
        output: 11
    """
    encoding = tiktoken.encoding_for_model(get_oai_chatmodel_tiktok(model))
    num_tokens = 2  # For "role" and "content" keys
    for key, value in message.items():
        num_tokens += len(encoding.encode(value))
    return num_tokens

def num_tokens_from_messagesa(message: Mapping[str, object], model: str) -> int:
    """
    Calculate the number of tokens required to encode a message.
    Args:
        message (Mapping): The message to encode, in a dictionary-like object.
        model (str): The name of the model to use for encoding.
    Returns:
        int: The total number of tokens required to encode the message.
    Example:
        message = {'role': 'user', 'content': 'Hello, how are you?'}
        model = 'gpt-3.5-turbo'
        num_tokens_from_messages(message, model)
        output: 11
    """

    encoding = tiktoken.encoding_for_model(get_oai_chatmodel_tiktok(model))
    num_tokens = 2  # For "role" and "content" keys
    for value in message.values():
        if isinstance(value, list):
            # For GPT-4-vision support, based on https://github.com/openai/openai-cookbook/pull/881/files
            for item in value:
                num_tokens += len(encoding.encode(item["text"]))
                
        elif isinstance(value, str):
            num_tokens += len(encoding.encode(value))
        else:
            raise ValueError(f"Could not encode unsupported message value type: {type(value)}")
    return num_tokens


def get_oai_chatmodel_tiktok(aoaimodel: str) -> str:
    message = "Expected Azure OpenAI ChatGPT model name"
    if aoaimodel == "" or aoaimodel is None:
        raise ValueError(message)
    if aoaimodel not in AOAI_2_OAI and aoaimodel not in MODELS_2_TOKEN_LIMITS:
        raise ValueError(message)
    return AOAI_2_OAI.get(aoaimodel) or aoaimodel