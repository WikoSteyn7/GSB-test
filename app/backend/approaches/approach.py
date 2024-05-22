# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
from core.messagebuilder import MessageBuilder
import tiktoken
from enum import Enum
import logging
from typing import Any,Sequence, AsyncGenerator, Awaitable, Callable, List, Optional, Union, cast
# from azure.search.documents.models import (
#     QueryCaptionResult,
#     QueryType,
#     VectorizedQuery,
#     VectorQuery,
# )

# class Document:
#     id: Optional[str]
#     content: Optional[str]
#     embedding: Optional[List[float]]
#     category: Optional[str]
#     sourcepage: Optional[str]
#     sourcefile: Optional[str]
#     oids: Optional[List[str]]
#     groups: Optional[List[str]]
#     captions: List[QueryCaptionResult]
#     score: Optional[float] = None
#     reranker_score: Optional[float] = None

#     def serialize_for_results(self) -> dict[str, Any]:
#         return {
#             "id": self.id,
#             "content": self.content,
#             "embedding": Document.trim_embedding(self.embedding),
#             "category": self.category,
#             "sourcepage": self.sourcepage,
#             "sourcefile": self.sourcefile,
#             "oids": self.oids,
#             "groups": self.groups,
#             "captions": (
#                 [
#                     {
#                         "additional_properties": caption.additional_properties,
#                         "text": caption.text,
#                         "highlights": caption.highlights,
#                     }
#                     for caption in self.captions
#                 ]
#                 if self.captions
#                 else []
#             ),
#             "score": self.score,
#             "reranker_score": self.reranker_score,
#         }

    # @classmethod
    # def trim_embedding(cls, embedding: Optional[List[float]]) -> Optional[str]:
    #     """Returns a trimmed list of floats from the vector embedding."""
    #     if embedding:
    #         if len(embedding) > 2:
    #             # Format the embedding list to show the first 2 items followed by the count of the remaining items."""
    #             return f"[{embedding[0]}, {embedding[1]} ...+{len(embedding) - 2} more]"
    #         else:
    #             return str(embedding)

    #     return None
    
#This class must match the Enum in app\frontend\src\api
class Approaches(Enum):
    RetrieveThenRead = 0
    ReadRetrieveRead = 1
    ReadDecomposeAsk = 2
    GPTDirect = 3
    ChatWebRetrieveRead = 4
    CompareWorkWithWeb = 5
    CompareWebWithWork = 6

class Approach:
    """
    An approach is a method for answering a question from a query and a set of
    documents.
    """
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    async def run(self, history: list[dict], overrides: dict, citation_lookup: dict[str, Any], thought_chain: dict[str, Any]) -> any:
        """
        Run the approach on the query and documents. Not implemented.

        Args:
            history: The chat history. (e.g. [{"user": "hello", "bot": "hi"}])
            overrides: Overrides for the approach. (e.g. temperature, etc.)
            citation_lookup: The dictionary for the citations.
            thought_chain: The dictionary for the thought chain.
        """
        raise NotImplementedError

    def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: list[dict[str, str]],
        user_content: str,
        max_tokens: int,
        few_shots=[],
    ) -> []:
        message_builder = MessageBuilder(system_prompt, model_id)

        # Add examples to show the chat what responses we want. It will try to mimic any responses and make sure they match the rules laid out in the system message.
        for shot in reversed(few_shots):
            message_builder.insert_message(shot.get("role"), shot.get("content"))

        append_index = len(few_shots) + 1

        message_builder.insert_message(self.USER, user_content, index=append_index)

        total_token_count = 0
        for existing_message in message_builder.messages:
            total_token_count += message_builder.count_tokens_for_message(existing_message)

        newest_to_oldest = list(reversed(history[:-1]))
        for message in newest_to_oldest:
            potential_message_count = message_builder.count_tokens_for_message(message)
            if (total_token_count + potential_message_count) > max_tokens:
                logging.info("Reached max tokens of %d, history will be truncated", max_tokens)
                break
            message_builder.insert_message(message["role"], message["content"], index=append_index)
            total_token_count += potential_message_count
        return message_builder.messages
    
        #Get the prompt text for the response length
    
    def get_response_length_prompt_text(self, response_length: int):
        """ Function to return the response length prompt text"""
        levels = {
            256: "summarised",
            1024: "standard",
            2048: "thorough",
        }
        level = levels[response_length]
        return f"Please provide a {level} answer. This means that your answer should be no more than {response_length} tokens long."

    def num_tokens_from_string(self, string: str, encoding_name: str) -> int:
        """ Function to return the number of tokens in a text string"""
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    
   