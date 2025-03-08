import os
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, module='grpc')

# Set environment variables before any other imports
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'
os.environ['GRPC_PYTHON_FORK_SUPPORT_ENABLED'] = '0'
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

import logging
from typing import List, Dict, Any, Callable, Optional, Tuple
import google.generativeai as genai
import google.generativeai.types as types
import re
import ast
from functions.text_file_read import ai_read_file
from functions.email_services import ai_send_email, ai_send_calendar_invite
import atexit
import grpc

# # Load environment variables from .env file
# load_dotenv()

# Initialize absl logging
# absl_logging.use_absl_handler()

# Fetch API key
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in environment variables.")

# Configure the API
genai.configure(api_key=API_KEY)

def get_system_promt_llm1(function_metadata:str)->str:
    prompt = f"""We are building an AI agent with two LLMs. \
        You are the first LLM, responsible for breaking down complex tasks into smaller subtasks.  
        Your outputs will be processed by the second LLM, which will execute the subtasks. 

        The second LLM will have access to:  
        1. Your outputs  
        2. The following Python functions:  

        {function_metadata}

        optionally, If use prompt suggests to read the perform_tasks.txt file, then here is the content of perform_tasks.txt

        {ai_read_file("perform_tasks.txt")}. 

        You are going to provide sub tasks for instructions in this file as well.
        However, if user prompt, doesn't suggest to read perform_tasks.txt file, then you going to ignore content of perform_tasks.txt file.

        ### Instructions for You:
        - Break down the task in a way that allows the second LLM to identify and call the necessary functions.  
        - Format your output as a **Python list** of subtasks.  
        - **Do not** include function names or arguments in your output.  
        - For email tasks, break them down like:
            - Send email reminder about assignment completion
            - Set up calendar reminder for Yoga Sadhana at 5:00 AM IST on specified date
        - For file organization tasks:
            - Retrieve list of all files within <folder name> 
            - Identify unique file types
            - Create organized folders based on the identified unique file types within the <folder name> directory.
            - Compress all images in "images" directory if directory exists
        - In each of your predictions, if required, do not just say "source folder", but always \
            say "source_path='<<<folder name>>>'" or "destination_path='<<<folder name>>>'".

        Your focus is on structuring the task effectively, ensuring smooth execution by the second LLM. 
        """
    
    return prompt

def get_system_promt_llm2(function_metadata:str)->str:
    prompt = f"""We are building an AI agent with two LLMs. The first LLM \
        has received a task from user and it sub-divided the complex task into smaller \
        sub-tasks. You are the second LLM in an AI agent system, responsible for executing subtasks. \
        You have access to the following Python functions that can be called to complete tasks:
        {function_metadata}

        ### Instructions for You:
        1. Analyze the subtask provided to you.
        2. Identify the most appropriate function to execute for this subtask.
        3. Format your response as a single function call with appropriate arguments.
        4. Use ONLY functions that exist in the provided list. Do not invent new functions.
        5. For email tasks:
           - Use ai_send_email(subject: str, body: str) for sending emails
           - Use ai_send_calendar_invite(subject: str, body: str, start_time: str, end_time: str, timezone: str) for calendar invites
           - Format datetime as 'YYYY-MM-DD HH:MM:SS'
           - Use 'Asia/Kolkata' for timezone

        Example Response Format:
        <<<
        user_input : Retrieve list of all files within the 'un_organized' folder
        response : ai_get_file_list(path='un_organized')

        user_input : Create organized folders based on the identified unique file types within the 'un_organized' directory
        response : ai_create_organized_folders(unique_file_types=unique_file_types, base_path='un_organized')

        user_input : Send email reminder for assignment
        response : ai_send_email(subject='Assignment Reminder', body='Please complete your assignment.')

        user_input : Set calendar reminder for Yoga Sadhana at 7:00 AM IST
        response : ai_send_calendar_invite(subject='Yoga Sadhana', body='Time for Yoga Sadhana!', start_time='2025-03-12 07:00:00', end_time='2025-03-12 07:30:00', timezone='Asia/Kolkata')
        >>>

        Your response should contain ONLY the function call, nothing else. Do not include any formatting like ``` or toolcode etc.
        """
    return prompt



def get_llm1_completion(system_prompt: str, user_prompt: str, model: str = "gemini-2.0-flash") -> str:
    """
    Generates a response using the first LLM (task decomposition).

    Args:
        system_prompt (str): The system prompt providing context.
        user_prompt (str): The user's input prompt.
        model (str): The AI model to use.

    Returns:
        str: The AI-generated response.
    """
    try:
        model = genai.GenerativeModel(model)
        response = model.generate_content(
            contents=[system_prompt, user_prompt],
            generation_config={"temperature": 0}
        )
        if not response:
            raise ValueError("Invalid response format from API.")

        return response.text.strip()
    
    except Exception as e:
        logging.error(f"Error generating response from LLM1: {e}")
        return "An error occurred while generating the response."

def get_llm2_completion(system_prompt: str, user_prompt: str, model: str = "gemini-2.0-flash") -> str:
    """
    Generates a response using the second LLM (task execution).

    Args:
        system_prompt (str): The system prompt providing context.
        user_prompt (str): The user's input prompt.
        model (str): The AI model to use.

    Returns:
        str: The AI-generated response.
    """
    try:
        model = genai.GenerativeModel(model)
        response = model.generate_content(
            contents=[system_prompt, user_prompt],
            generation_config={"temperature": 0}
        )
        if not response:
            raise ValueError("Invalid response format from API.")

        return response.text.strip()
    
    except Exception as e:
        logging.error(f"Error generating response from LLM2: {e}")
        return "An error occurred while generating the response."
    
def process_llm1_response(response: str) -> List[str]:
    """
    Process the first LLM response to extract the subtask list.
    
    Args:
        response (str): The raw response from the LLM.
        
    Returns:
        List[str]: The extracted list of subtasks.
    """
    try:
        # Try multiple approaches to extract the list
        # First, try to find with square brackets
        match = re.search(r"\[(.*?)\]", response, re.DOTALL)
        if match:
            extracted_list = match.group(0)  # Includes square brackets
            return ast.literal_eval(extracted_list)  # Convert to Python list
            
        # Alternative approach: Look for lines that might be list items
        lines = response.split('\n')
        potential_list = []
        for line in lines:
            # Look for numbered or bulleted list items
            clean_line = re.sub(r'^\s*[\d\-\*]+\.\s*', '', line).strip()
            if clean_line and line != clean_line:
                potential_list.append(clean_line)
                
        if potential_list:
            return potential_list
            
        # If all else fails, return the entire response as a single item
        return [response.strip()]
            
    except (SyntaxError, ValueError) as e:
        logging.error(f"Error parsing LLM1 response: {e}")
        logging.error(f"Raw response: {response}")
        return []

# Register cleanup function
# def process_to_perform_tasks():
#     """Process tasks from perform_tasks.txt file"""
#     try:
#         # Read the tasks file
#         tasks_content = ai_read_file("perform_tasks.txt")
        
#         # Send email about assignment
#         email_subject = "Assignment Reminder"
#         email_body = "Please complete your assignment."
#         ai_send_email(subject=email_subject, body=email_body)
        
#         # Send calendar invite for Yoga Sadhana
#         calendar_subject = "Yoga Sadhana Reminder"
#         calendar_body = "Time for your daily Yoga Sadhana!"
#         start_time = "2025-03-14 05:00:00"  # 5:00 AM IST on 14-March-2025
#         end_time = "2025-03-14 05:30:00"    # 30 minutes duration
#         timezone = "Asia/Kolkata"
        
#         ai_send_calendar_invite(
#             subject=calendar_subject,
#             body=calendar_body,
#             start_time=start_time,
#             end_time=end_time,
#             timezone=timezone
#         )
        
#         logging.info("Successfully processed perform_tasks.txt tasks")
#     except Exception as e:
#         logging.error(f"Error processing perform_tasks.txt: {e}")

# if __name__ == "__main__":
#     # Process to perform tasks
#     process_to_perform_tasks()
