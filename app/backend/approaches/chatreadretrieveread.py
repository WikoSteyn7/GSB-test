 # Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import json
import re
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Coroutine, Sequence
import asyncio

import openai
from openai import AzureOpenAI
from openai import  AsyncAzureOpenAI
from approaches.approach import Approach
# from azure.search.documents import SearchClient  
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import RawVectorQuery
from azure.search.documents.models import QueryType
from azure.storage.blob import (
    AccountSasPermissions,
    BlobServiceClient,
    ResourceTypes,
    generate_account_sas,
)
from text import nonewlines
from core.modelhelper import get_token_limit, num_tokens_from_messages,num_tokens_from_messagesa
import requests
import tiktoken

class ChatReadRetrieveReadApproach(Approach):
    """Approach that uses a simple retrieve-then-read implementation, using the Azure AI Search and
    Azure OpenAI APIs directly. It first retrieves top documents from search,
    then constructs a prompt with them, and then uses Azure OpenAI to generate
    an completion (answer) with that prompt."""
     


    SYSTEM_PROPRIETARY_DATA = """
You are a {prompt_industry} AI {system_persona}. Your goal is to help {user_title} to get accurate information from their company documents.
It is vital to help the user and you will be rewarded for your effort.
Please follow the three steps below to ensure accurate and consistent information:

Step One:
**Objective**: Your task is to retrieve relevant information from the provided sources.
**Sources**: Refer to the section below <<<Sources:>>>.
**Instructions**: Thoroughly review all sources

Step two:
**Objective**: 
-  Answer ONLY with the facts listed in the list of sources below with citations. 
-  Avoid making assumptions, generating speculative or generalized information or adding personal opinions. 
**Format**:
- Follow the user query for specifics to what they want.
- For comparative queries: Utilize bullet points e.g. • if applicable otherwise use paragraphs. 
- For procedural queries: Present the information in a step-by-step format using numbers e.g. 1,2,3.
- You are not allowed to use any other information except for information gathered in the Sources below as indicated in Step One.
- If information for a query is unavailable in the sources, clearly state that you do not have the necessary information.
- When presenting tabular information, always format it as an HTML table.
- Never mention a source that is not relevant.
- Use double stars to emphasise important information e.g. **Main Income Sources**
- Conclude with a statement like "For detailed specifics, please contact the company. How may I further assist you?"
- Always answer in the language used by the user in the query.
**Details**: Be detailed in your responses, but only give highly relevant information to the user query.   
**Consistency**: Consistency is key. The same query should yield consistent answers in the future.
**Sourcing**: 
- Each source has a "FileX" moniker like this | File1 | :  followed by a colon and the actual information. Always use square brackets in your response to reference the source, e.g. [File1]. Don't combine sources, list each source separately, e.g. [File1][File2] 
- Include a source at the end of each fact or bullet point.
- Every table must always include a source at the bottom.
- It is very important to have the correct format for every source document
**Summary**: 
- At the end of each response create a four word summary. Use double hashtag for the summary e.g. ##Summary of Net Income##

Step Three:
- Reflect to ensure your answer is accurate, clear and consistent and that each answer has the correct source. 
- If there are any numbers in your response, ensure that it is accurate and corresponds with the source data. 
- Make sure all three steps are completed. Feel free to ask if you have any questions that might help you produce a better answer.
"""
    
    SYSTEM_INTDUSTRY_COMPARISON="""
You are a {prompt_industry} AI {system_persona}. Your goal is to help {user_title} to compare documents from different companies.
It is vital to help the user and you will be rewarded for your effort.
Please follow the three steps below to ensure accurate and consistent information:

Step One:
**Objective**: 
- Your task is to retrieve information regarding the companies specified in the Sources below.
**Sources**:
{sources_section}
**Instructions**: 
- Thoroughly review all sources, ensuring that information from the different companies remains distinct and separate.

Step two:
**Objective**: 
- Answer ONLY with the facts listed in the list of sources below with citations. 
- Avoid making assumptions, generating speculative or generalized information or adding personal opinions. 
- Respond accurately to each query for each company, but keep them separate and never mix different company sources. 
**Format**:
- Follow the user query for specifics to what they want.
- For comparative queries: Utilize bullet points e.g. • for each company if applicable otherwise use paragraphs. 
- For procedural queries: Present the information in a step-by-step format for each company using numbers e.g. 1,2,3.
- You are not allowed to use any other information except for information gathered in the Sources below as indicated in Step One.
- If information for a company is unavailable in the sources, clearly state that you do not have the necessary information for that company.
- When presenting tabular information, format it as an HTML table.
- Never mention a source that is not relevant.
- Use double stars to emphasise important information e.g. **Main Income Sources**
- Conclude with a statement like "For detailed specifics, please contact the company. How may I further assist you?"
**Details**: Be detailed in your responses, but only give information that is highly relevant to the user query.   
**Consistency**: Consistency is key. The same query should yield consistent answers in the future.
**Sourcing**: 
- Each source has a "FileX" moniker like this |File1| :  followed by a colon and the actual information. Always use square brackets in your response to reference the source, e.g. [File1]. Don't combine sources, list each source separately, e.g. [File1][File2] 
- Include a source at the end of each fact or bulletpoint.
- Every table must always include a source at the bottom.
- It is very important to have the correct format for every source document
**Summary**: 
- At the end of each response create a four word summary. Use double hashtag for the summary e.g. ##Summary of Net Income##

Step Three:
- Reflect to ensure your answer is accurate, clear and consistent and that each answer has the correct source. 
- If there are any numbers in your response, ensure that it is accurate and correspond with the source data. 
- Make sure all three steps are completed. Please ask if you have any questions that might help you produce a better answer.
"""
    

    FOLLOW_UP_QUESTIONS_PROMPT_CONTENT = """
ALWAYS generate three very brief unordered follow-up questions surrounded by triple chevrons (<<<Are there exclusions for prescriptions?>>>) that the user would likely ask next about their agencies data. 
Surround each follow-up question with triple chevrons (<<<Are there exclusions for prescriptions?>>>). Try not to repeat questions that have already been asked.
Only generate follow-up questions and do not generate any text before or after the follow-up questions, such as 'Next Questions'
"""

    QUERY_PROMPT_TEMPLATE = """
Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in source documents.
Generate a search query based on the conversation and the new question. Treat each search term as an individual keyword. Do not combine terms in quotes or brackets.
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<<>>> in the search query terms.
Do not include any special characters like '+'.
If you cannot generate a search query, return just the number 0.
    """

    QUERY_PROMPT_FEW_SHOTS = [
        {'role' : Approach.USER, 'content' : 'What are the future plans for public transportation development?' },
        {'role' : Approach.ASSISTANT, 'content' : 'Future plans for public transportation' },
        {'role' : Approach.USER, 'content' : 'how much renewable energy was generated last year?' },
        {'role' : Approach.ASSISTANT, 'content' : 'Renewable energy generation last year' }
    ]

    RESPONSE_PROMPT_FEW_SHOTS = [
        {"role": Approach.USER ,'content': 'I am looking for information in source documents'},
        {'role': Approach.ASSISTANT, 'content': 'user is looking for information in source documents. Do not provide answers that are not in the source documents'},
        {'role': Approach.USER, 'content': 'What steps are being taken to promote energy conservation?'},
        {'role': Approach.ASSISTANT, 'content': 'Several steps are being taken to promote energy conservation including reducing energy consumption, increasing energy efficiency, and increasing the use of renewable energy sources.Citations[File0]'}
    ]
    
    
    def __init__(
        self,
        search_client: SearchClient,
        oai_endpoint: str,
        oai_service_key: str,
        chatgpt_deployment: str,
        source_file_field: str,
        content_field: str,
        page_number_field: str,
        chunk_file_field: str,
        file_name_field: str,
        content_storage_container: str,
        blob_client: BlobServiceClient,
        query_term_language: str,
        model_name: str,
        model_version: str,
        target_embedding_model: str,
        enrichment_appservice_uri: str,
        target_translation_language: str,
        enrichment_endpoint:str,
        enrichment_key:str,
        azure_ai_translation_domain: str,
        use_semantic_reranker: bool
        
    ):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.source_file_field = source_file_field
        self.content_field = content_field
        self.page_number_field = page_number_field
        self.file_name_field = file_name_field
        self.chunk_file_field = chunk_file_field
        self.content_storage_container = content_storage_container
        self.blob_client = blob_client
        self.query_term_language = query_term_language
        self.chatgpt_token_limit = get_token_limit(model_name)
        #escape target embeddiong model name
        self.escaped_target_model = re.sub(r'[^a-zA-Z0-9_\-.]', '_', target_embedding_model)
        self.target_translation_language=target_translation_language
        self.enrichment_endpoint=enrichment_endpoint
        self.enrichment_key=enrichment_key
        self.oai_endpoint=oai_endpoint
        self.embedding_service_url = enrichment_appservice_uri
        self.azure_ai_translation_domain=azure_ai_translation_domain
        self.use_semantic_reranker=use_semantic_reranker
        
        openai.api_base = oai_endpoint
        openai.api_type = 'azure'
        openai.api_key = oai_service_key
        openai.api_version = "2024-02-01"
        
        self.client = AsyncAzureOpenAI(
        azure_endpoint = openai.api_base, 
        api_key=openai.api_key,  
        api_version=openai.api_version)
               

        self.model_name = model_name
        self.model_version = model_version
        
       
      
        
    # def run(self, history: list[dict], overrides: dict) -> any:
    async def run(self, user:dict[str, Any], query: Sequence[dict[str, Any]], ai_config: dict[str, Any] ) -> Any:

        log = logging.getLogger("uvicorn")
        log.setLevel('DEBUG')
        log.propagate = True
        thought_chain={}
        chat_completion = None
        use_semantic_captions = True if ai_config.get("semantic_captions") else False
        top = ai_config.get("top") or 3
        user_persona = ai_config.get("user_persona", "")
        system_persona = ai_config.get("system_persona", "")
        response_length = int(ai_config.get("response_length") or 1024)
        company_filter = query.get("selected_companies", "")
        years_filter = query.get("selected_years", "")
        industry_comparison = True if query.get("industry_comparison") else False
        document_filter = query.get("selected_document_type", "")
        minimum_search_score = ai_config.get("minimum_search_score", 0.0)
        minimum_reranker_score = ai_config.get("minimum_reranker_score", 0.0)
        
        user_entity = user.get("legal_entity") 
        user_industry = user.get("industry")
        user_title = user.get("user_access_level")
        

        history = query.get("messages")
        original_user_query = history[-1]["content"]
        user_query_request = 'Generate search query for: ' + history[-1]["content"]
        thought_chain["work_query"] = user_query_request

        # Detect the language of the user's question
        # detectedlanguage = self.detect_language(original_user_query)

        # if detectedlanguage != self.target_translation_language:
        #     user_question = self.translate_response(original_user_query, self.target_translation_language)
        # else:
        #     user_question = original_user_query

        # query_prompt=self.QUERY_PROMPT_TEMPLATE.format(query_term_language=self.query_term_language)

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        # messages = self.get_messages_from_history(
        #     query_prompt,
        #     self.model_name,
        #     history,
        #     user_question,
        #     self.chatgpt_token_limit - len(user_question),
        #     self.QUERY_PROMPT_FEW_SHOTS,
        #     )

        # try:
        #     chat_completion= await self.client.chat.completions.create(
        #             model=self.chatgpt_deployment,
        #             messages=messages,
        #             temperature=0.0,
        #             # max_tokens=32, # setting it too low may cause malformed JSON
        #             max_tokens=100,
        #         n=1)
        
        # except Exception as e:
        #     log.error(f"Error generating optimized keyword search: {str(e)}")
        #     yield json.dumps({"error": f"Error generating optimized keyword search: {str(e)}"}) + "\n"
        #     return

        # generated_query = chat_completion.choices[0].message.content
        
        # #if we fail to generate a query, return the last user question
        # if generated_query.strip() == "0":
        #     generated_query = history[-1]["content"]

        # thought_chain["work_search_term"] = generated_query
        
        # Generate embedding using REST API
        url = f'{self.embedding_service_url}/models/{self.escaped_target_model}/embed'
        data = [f'"{original_user_query}"']
        
        headers = {
                'Accept': 'application/json',  
                'Content-Type': 'application/json',
            }
        embedded_query_vector = list[float]
        try:
            response = requests.post(url, json=data,headers=headers,timeout=60)
            if response.status_code == 200:
                response_data = response.json()
                embedded_query_vector =response_data.get('data')          
            else:
                # Generate an error message if the embedding generation fails
                log.error(f"Error generating embedding:: {response.status_code}")
                yield json.dumps({"error": "Error generating embedding"}) + "\n"
                return # Go no further
        except Exception as e:
            # Timeout or other error has occurred
            log.error(f"Error generating embedding: {str(e)}")
            yield json.dumps({"error": f"Error generating embedding: {str(e)}"}) + "\n"
            return # Go no further
        
        #vector set up for pure vector search & Hybrid search & Hybrid semantic
        vector = RawVectorQuery(vector=embedded_query_vector, k=top, fields="contentVector")

        document_filter = ','.join(document_filter)  
        
        years_filter = ' or year eq '.join(years_filter)
       
        company_filter_list = company_filter
        
        results = []
        search_filter =[]
        data_points = []
        citation_lookup = {}
        
        
            # company_filter_list = user_entity

        #for company in company_filter:
        #Create a filter for the search query
        if industry_comparison:
            tasks = [
                self.perform_search(company, vector, document_filter, years_filter, self.use_semantic_reranker, ai_config, self.search_client, top, original_user_query)
                for company in company_filter_list
            ]

            search_results = await asyncio.gather(*tasks)

            file_counter = 0  # Initialize a counter for file numbers

            for idx, company_results in enumerate(search_results):
                for doc_idx, doc in enumerate(company_results):
                    results.append(
                        " <<<" + nonewlines(doc["entity"]) + " Source:>>>" + f"|File{file_counter}" + "| :" + nonewlines(doc[self.content_field])
                    )
                    data_points.append(
                        "/".join(urllib.parse.unquote(doc[self.source_file_field]).split("/")[4:]) + "| " + nonewlines(doc[self.content_field])
                    )
                    citation_lookup[f"File{file_counter}"] = {
                        "citation": str(doc[self.file_name_field]),
                        "source_path": self.get_source_file_with_sas(doc[self.source_file_field]),
                        "page_number": str(doc[self.page_number_field][0]) or "0",
                    }
                    file_counter += 1  # Increment the counter for each document
                
        
        else:
            company_filter_list = user_entity              
            search_filter = f"search.in(entity, '{company_filter_list}', ',')"

                
            if (document_filter != "") & (document_filter != "All"):
                search_filter = search_filter + f" and search.in(document_type, '{document_filter}', ',')"
            
            if years_filter != "" :
                search_filter = search_filter + f" and (year eq {years_filter})"
               
            if (self.use_semantic_reranker and ai_config.get("semantic_ranker")):
                    r = self.search_client.search(
                        search_text = None,
                        query_type=QueryType.SEMANTIC,
                        semantic_configuration_name="default",
                        top=top,
                        query_caption="extractive|highlight-false"
                        if use_semantic_captions else None,
                        vector_queries =[vector],
                        filter=search_filter
                    )
            else:
                r = self.search_client.search(
                    original_user_query, top=top,vector_queries=[vector], filter=search_filter
                )
                
            
                    
            for idx, doc in enumerate(r):  # for each document in the search results
                # include the "FileX" moniker in the prompt, and the actual file name in the response
                results.append(
                " <<<Source:>>>" + f"|File{idx}" + "| :" + nonewlines(doc[self.content_field])
                )
                data_points.append(
                "/".join(urllib.parse.unquote(doc[self.source_file_field]).split("/")[4:]
                    ) + "| " + nonewlines(doc[self.content_field])
                    )
                # uncomment to debug size of each search result content_field
                # print(f"File{idx}: ", self.num_tokens_from_string(f"File{idx} " + /
                #  "| " + nonewlines(doc[self.content_field]), "cl100k_base"))

                # add the "FileX" moniker and full file name to the citation lookup
                citation_lookup[f"File{idx}"] = {
                    "citation": str(doc[self.file_name_field]),
                    "source_path": self.get_source_file_with_sas(doc[self.source_file_field]),
                    "page_number": str(doc[self.page_number_field][0]) or "0",
                }
                
                    
                    
           
        # create a single string of all the results to be used in the prompt
        results_text = "".join(results)
        if results_text == "":
            content = "\n NONE"
        else:
            content = "\n " + results_text

        # STEP 3: Generate the prompt to be sent to the GPT model
        follow_up_questions_prompt = (
            self.FOLLOW_UP_QUESTIONS_PROMPT_CONTENT
            if ai_config.get("suggest_followup_questions")
            else ""
        )
        
        sources_section = ""
        if industry_comparison is True:
            system_message = self.SYSTEM_INTDUSTRY_COMPARISON
            for company in company_filter:
                sources_section += f"- For {company}: Refer to the section below <<< {company} Sources: >>>\n"

            system_message = system_message.format(
                prompt_industry=user_industry,
                system_persona =system_persona,
                user_title = user_title,
                sources_section=sources_section,
                query_term_language=self.query_term_language,
                injected_prompt="",
                follow_up_questions_prompt=follow_up_questions_prompt,
                response_length_prompt=self.get_response_length_prompt_text(response_length),
                userPersona=user_persona,
                )
        else:
            system_message = self.SYSTEM_PROPRIETARY_DATA
            system_message = system_message.format(
                prompt_industry=user_industry,
                system_persona=system_persona,
                user_title = user_title,
                injected_prompt="",
                follow_up_questions_prompt=follow_up_questions_prompt,
                response_length_prompt=self.get_response_length_prompt_text(response_length),
                userPersona=user_persona,
                systemPersona=system_persona,
            )

        # Allow client to replace the entire prompt, or to inject into the existing prompt using >>>
        prompt_override = ai_config.get("prompt_template")

        # if prompt_override is None or prompt_override == "default":
        #     system_message = system_message.format(
        #         prompt_industry = user_industry,
        #         company1=company_filter[0],
        #         company2= company_filter[1],
        #         query_term_language=self.query_term_language,
        #         injected_prompt="",
        #         follow_up_questions_prompt=follow_up_questions_prompt,
        #         response_length_prompt=self.get_response_length_prompt_text(
        #             response_length
        #         ),
        #         userPersona=user_persona,
        #         systemPersona=system_persona,
        #     )
        # elif prompt_override.startswith(">>>"):
        #     system_message = system_message.format(
        #         query_term_language=self.query_term_language,
        #         injected_prompt=prompt_override[3:] + "\n ",
        #         follow_up_questions_prompt=follow_up_questions_prompt,
        #         response_length_prompt=self.get_response_length_prompt_text(
        #             response_length
        #         ),
        #         userPersona=user_persona,
        #         systemPersona=system_persona,
        #     )
        # else:
        #     system_message = system_message.format(
        #         query_term_language=self.query_term_language,
        #         follow_up_questions_prompt=follow_up_questions_prompt,
        #         response_length_prompt=self.get_response_length_prompt_text(
        #             response_length
        #         ),
        #         userPersona=user_persona,
        #         systemPersona=system_persona,
        #     )
            
        user_query_tokens = num_tokens_from_messages({"role": "user", "content": original_user_query}, self.model_name)
        sytem_prompt_tokens=num_tokens_from_messages({"role": "user", "content": system_message}, self.model_name)
        content_tokens= num_tokens_from_messages({"role": "user", "content": content}, self.model_name) 
        history_tokens = 0
        for item in history:
            history_content = item         
            history_tokens += num_tokens_from_messagesa(history_content, self.model_name)

            
        try:
            # STEP 3: Generate a contextual and content-specific answer using the search results and chat history.
            #Added conditional block to use different system messages for different models.
            if self.model_name.startswith("gpt-35-turbo"):
                messages = self.get_messages_from_history(
                    system_message,
                    self.model_name,
                     history,
                    history[-1]["content"] + "Sources:\n" + content + "\n\n", # 3.5 has recency Bias that is why this is here
                    max_tokens=self.chatgpt_token_limit - 500
                                       
                )
                
            

                #Uncomment to debug token usage.
                #print(messages)
                #message_string = ""
                #for message in messages:
                #    # enumerate the messages and add the role and content elements of the dictoinary to the message_string
                #    message_string += f"{message['role']}: {message['content']}\n"

                
                
              
                chat_completion= await self.client.chat.completions.create(
                model=self.chatgpt_deployment,
                messages=messages,
                temperature=float(ai_config.get("response_temp")) or 0.6,
                n=1,
                stream=True
                )


            elif self.model_name.startswith("gpt-4"):
                messages = self.get_messages_from_history(
                    system_prompt=system_message,
                    # "Sources:\n" + content + "\n\n" + system_message,
                    model_id=self.model_name,
                    history=history,
                    # history[-1]["user"],
                    user_content=history[-1]["content"] + content + "\n\n", # GPT 4 starts to degrade with long system messages. so moving sources here 
                    max_tokens=self.chatgpt_token_limit
                    )

                #Uncomment to debug token usage.
                #print(messages)
                #message_string = ""
                #for message in messages:
                #    # enumerate the messages and add the role and content elements of the dictoinary to the message_string
                #    message_string += f"{message['role']}: {message['content']}\n"
                #print("Content Tokens: ", self.num_tokens_from_string("Sources:\n" + content + "\n\n", "cl100k_base"))
                #print("System Message Tokens: ", self.num_tokens_from_string(system_message, "cl100k_base"))
                #print("Few Shot Tokens: ", self.num_tokens_from_string(self.response_prompt_few_shots[0]['content'], "cl100k_base"))
                #print("Message Tokens: ", self.num_tokens_from_string(message_string, "cl100k_base"))
                               
                chat_completion= await self.client.chat.completions.create(
                model=self.chatgpt_deployment,
                messages=messages,
                seed = 42,
                max_tokens=response_length,
                temperature=float(ai_config.get("response_temp")) or 0.2,
                n=1,
                stream=True
                
            )
        # STEP 4: Format the response
        # msg_to_display = '\n\n'.join([str(message) for message in messages])
        # generated_response=chat_completion.choices[0].message.content

        # # # Detect the language of the response
        # response_language = self.detect_language(generated_response)
        # #if response is not in user's language, translate it to user's language
        # if response_language != detectedlanguage:
        #     translated_response = self.translate_response(generated_response, detectedlanguage)
        # else:
        #     translated_response = generated_response
        # thought_chain["work_response"] = urllib.parse.unquote(translated_response)
            msg_to_display = '\n\n'.join([str(message) for message in messages])
            print(msg_to_display)
            result = []
            initial_data = {
                # "data_points":data_points,
                # "thoughts": f"Searched for:<br>{original_user_query}<br><br>Conversations:<br>" + msg_to_display.replace('\n', '<br>'),
                # "thought_chain":thought_chain,
                "work_citation_lookup":citation_lookup,
                # "web_citation_lookup": {}
                } 
            
            print(f"{json.dumps(initial_data)}")
            yield json.dumps(initial_data) + "\n"
        
            # STEP 4: Format the response
            async for event_chunk in chat_completion:
                if event_chunk.choices:
                # Check if there is at least one element and the first element has the key 'delta'
                    if event_chunk.choices[0].delta.content:
                        content = event_chunk.choices[0].delta.content
                        # print (content)
                        result.append(content)
                        # print(f'{{"data": {json.dumps(content)}}}\n\n')
                        yield json.dumps({"content": content}) + "\n"
            completion_tokens = num_tokens_from_messages({"role": "user", "content":"".join(result)}, "gpt-4")
            token_ussage = {
                "user_query_tokens" : user_query_tokens,
                "sytem_prompt_tokens": sytem_prompt_tokens,
                "content_tokens": content_tokens,
                "history_tokens": history_tokens, 
                "completion_tokens": completion_tokens,  
                "model": self.model_name              
            }
            print(f"{json.dumps(token_ussage)}")
            yield json.dumps(token_ussage) + "\n"
            # yield (f'event: end\ndata: Stream ended\n\n')
        except Exception as e:
            print(e)
            yield json.dumps({"error": f"Error generating chat completion: {str(e)}"}) + "\n"
            return


            # yield f"{json.dumps({'error': str(e)})}\n\n"
            
            
    def detect_language(self, text: str) -> str:
        """ Function to detect the language of the text"""
        try:
            endpoint_region = self.enrichment_endpoint.split("https://")[1].split(".api")[0]
            api_detect_endpoint = f"https://{self.azure_ai_translation_domain}/detect?api-version=3.0"
            headers = {
                'Ocp-Apim-Subscription-Key': self.enrichment_key,
                'Content-type': 'application/json',
                'Ocp-Apim-Subscription-Region': endpoint_region
            }
            data = [{"text": text}]
            response = requests.post(api_detect_endpoint, headers=headers, json=data)

            if response.status_code == 200:
                detected_language = response.json()[0]['language']
                return detected_language
            else:
                raise Exception(f"Error detecting language: {response.status_code}")
        except Exception as e:
            raise Exception(f"An error occurred during language detection: {str(e)}") from e
     
    def translate_response(self, response: str, target_language: str) -> str:
        """ Function to translate the response to target language"""
        endpoint_region = self.enrichment_endpoint.split("https://")[1].split(".api")[0]      
        api_translate_endpoint = f"https://{self.azure_ai_translation_domain}/translate?api-version=3.0"
        headers = {
            'Ocp-Apim-Subscription-Key': self.enrichment_key,
            'Content-type': 'application/json',
            'Ocp-Apim-Subscription-Region': endpoint_region
        }
        params={'to': target_language }
        data = [{
            "text": response
        }]          
        response = requests.post(api_translate_endpoint, headers=headers, json=data, params=params)
        
        if response.status_code == 200:
            translated_response = response.json()[0]['translations'][0]['text']
            return translated_response
        else:
            raise Exception(f"Error translating response: {response.status_code}")

    def get_source_file_with_sas(self, source_file: str) -> str:
        """ Function to return the source file with a SAS token"""
        try:
            sas_token = generate_account_sas(
                self.blob_client.account_name,
                self.blob_client.credential.account_key,
                resource_types=ResourceTypes(object=True, service=True, container=True),
                permission=AccountSasPermissions(
                    read=True,
                    write=True,
                    list=True,
                    delete=False,
                    add=True,
                    create=True,
                    update=True,
                    process=False,
                ),
                expiry=datetime.utcnow() + timedelta(hours=1),
            )
            return source_file + "?" + sas_token
        except Exception as error:
            logging.error(f"Unable to parse source file name: {str(error)}")
            return ""
        
    def num_tokens_from_string(self, string: str, encoding_name: str) -> int:
        """ Function to return the number of tokens in a text string"""
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    
    async def perform_search(self, company: str, vector: Any, document_filter: str, years_filter: str, use_semantic_reranker: bool, ai_config: dict[str, Any], search_client: Any, top: int, original_user_query: str):
        search_filter = f"search.in(entity, '{company}', ',')"

        if document_filter != "" and document_filter != "All":
            search_filter += f" and search.in(document_type, '{document_filter}', ',')"

        if years_filter != "":
            search_filter += f" and (year eq {years_filter})"

        if use_semantic_reranker and ai_config.get("semantic_ranker"):
            r = search_client.search(
                search_text=None,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default",
                top=top,
                query_caption= None,
                vector_queries=[vector],
                filter=search_filter
            )
        else:
            r = search_client.search(
                original_user_query, top=top, vector_queries=[vector], filter=search_filter
            )

        return r