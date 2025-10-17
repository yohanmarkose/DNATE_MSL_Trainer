from dotenv import load_dotenv
import os
from openai import OpenAI
import json
from typing import Optional
from datetime import datetime
from services.s3 import S3FileManager  # Updated import path

load_dotenv()

# Load environment variables
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate environment variables
if not AWS_BUCKET_NAME:
    raise ValueError("AWS_BUCKET_NAME environment variable is not set!")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set!")

print(f"Using bucket: {AWS_BUCKET_NAME}")  # Debug print

client = OpenAI(api_key=OPENAI_API_KEY)

MODEL_ANSWERS_FILE = "model_answers.json"

# Load JSON files
# with open('questions.json', 'r') as f:
#     questions_data = json.load(f)

# with open('personas.json', 'r') as f:
#     personas_data = json.load(f)

# S3 configuration
DOCUMENTS_KEY = "model_answers.json"
BASE_PATH = "model_answer"

# Initialize S3 manager
s3_manager = S3FileManager(AWS_BUCKET_NAME, BASE_PATH)


def save_to_s3(save_data, key=DOCUMENTS_KEY):
    """Save model answers to S3"""
    try:
        # Validate input
        if save_data is None:
            raise ValueError("save_data is None")
        
        # Convert dict to JSON string
        json_string = json.dumps(save_data, indent=2)
        
        # Construct full S3 key path
        full_key = f"{BASE_PATH}/{key}"
        
        print(f"Uploading to S3: s3://{AWS_BUCKET_NAME}/{full_key}")
        
        # Upload to S3
        s3_manager.upload_file(
            bucket_name=AWS_BUCKET_NAME,
            file_name=full_key,
            content=json_string
        )
        print(f"✅ Saved to S3: s3://{AWS_BUCKET_NAME}/{full_key}")
    except Exception as e:
        print(f"❌ Error saving to S3: {str(e)}")
        import traceback
        traceback.print_exc()

def load_from_s3(key=DOCUMENTS_KEY):
    """Load model answers from S3"""
    try:
        # Construct full S3 key path
        full_key = f"{BASE_PATH}/{key}"
        
        # Load from S3
        json_content = s3_manager.load_s3_file_content(full_key)
        
        # Parse JSON string to dict
        data = json.loads(json_content)
        print(f"✅ Loaded from S3: s3://{AWS_BUCKET_NAME}/{full_key}")
        return data
    except Exception as e:
        print(f"❌ Error loading from S3: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"answers": {}}


def load_model_answers():
    """Load model answers from local file or S3"""
    # Try local file first
    # if os.path.exists(MODEL_ANSWERS_FILE):
    #     with open(MODEL_ANSWERS_FILE, 'r') as f:
    #         return json.load(f)
    
    # If local doesn't exist, try S3
    print("load from S3...")
    return load_from_s3()


def save_model_answers(data):
    """Save model answers to both local file and S3"""
    # Save locally
    with open(MODEL_ANSWERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved locally to {MODEL_ANSWERS_FILE}")
    
    # Save to S3
    save_to_s3(data)


# Load existing model answers
model_answers_data = load_model_answers()


def get_answer_key(question_id: int, persona_id: Optional[str] = None):
    """Create a unique key for caching"""
    if persona_id:
        return f"q{question_id}_{persona_id}"
    return f"q{question_id}_generic"


def generate_all_model_answers():
    """
    Run this function once to generate all model answers.
    Call it from Python directly, not as an API endpoint.
    """
    print("Starting model answer generation...")
    
    generated_answers = {}
    questions = questions_data["questions"]
    personas = personas_data["personas"]
    
    for question in questions:
        question_id = question["id"]
        
        # Generate generic answer
        print(f"Generating generic answer for Q{question_id}...")
        answer_key = get_answer_key(question_id)
        
        model_prompt = f"""Create a model answer for an MSL responding to this physician question.

Question: {question['question']}
Category: {question['category']}
Context: {question['context']}
Key Themes to Cover: {', '.join(question.get('key_themes', []))}

Create a strong MSL response (200-250 words) that:
1. Directly addresses the question
2. Covers the key themes
3. Is evidence-based and professional

Provide your response in this format:
MODEL ANSWER:
[Your detailed response here]

KEY POINTS:
- Point 1
- Point 2
- Point 3
- Point 4

REASONING:
[Brief explanation of the approach]"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert MSL trainer creating model answers."},
                    {"role": "user", "content": model_prompt}
                ],
                temperature=0.5,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            
            # Parse the response
            sections = content.split("KEY POINTS:")
            model_answer = ""
            key_points = []
            reasoning = ""
            
            if len(sections) > 1:
                model_answer = sections[0].replace("MODEL ANSWER:", "").strip()
                remaining = sections[1].split("REASONING:")
                if len(remaining) > 1:
                    key_points_text = remaining[0].strip()
                    key_points = [line.strip('- ').strip() for line in key_points_text.split('\n') if line.strip().startswith('-')]
                    reasoning = remaining[1].strip()
            else:
                model_answer = content
                key_points = question.get('key_themes', [])
            
            generated_answers[answer_key] = {
                "question_id": question_id,
                "persona_id": None,
                "persona_name": None,
                "question": question["question"],
                "category": question["category"],
                "difficulty": question.get("difficulty", "medium"),
                "context": question["context"],
                "estimated_response_time": question.get("estimated_response_time", 60),
                "model_answer": model_answer,
                "key_points": key_points if key_points else question.get('key_themes', []),
                "reasoning": reasoning,
                "persona_tailored": False,
                "generated_at": datetime.now().isoformat()
            }
            
            print(f"✓ Generated generic answer for Q{question_id}")
            
        except Exception as e:
            print(f"✗ Error generating generic answer for Q{question_id}: {str(e)}")
        
        # Generate persona-specific answers
        for persona in personas:
            persona_id = persona["id"]
            
            # Only generate if this persona is relevant for this question
            if persona_id in question.get("persona", []):
                print(f"Generating answer for Q{question_id} + {persona_id}...")
                answer_key = get_answer_key(question_id, persona_id)
                
                persona_prompt = f"""Create a model answer for an MSL responding to this physician question.

Question: {question['question']}
Category: {question['category']}
Context: {question['context']}
Key Themes to Cover: {', '.join(question.get('key_themes', []))}

Physician Persona:
- {persona['name']}, {persona['specialty']}
- Practice Setting: {persona['practice_setting']['type']}
- Priorities: {', '.join(persona['priorities'][:3])}
- Communication Style: {persona['communication_style']['tone']}
- Engagement Tips: {', '.join(persona['engagement_tips'][:3])}

Create a strong MSL response (200-250 words) that:
1. Directly addresses the question
2. Covers the key themes
3. Uses appropriate communication style for this specific persona
4. Addresses their specific priorities
5. Is evidence-based and professional

Provide your response in this format:
MODEL ANSWER:
[Your detailed response here]

KEY POINTS:
- Point 1
- Point 2
- Point 3
- Point 4

REASONING:
[Brief explanation of why this approach works for this persona]"""

                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert MSL trainer creating persona-tailored model answers."},
                            {"role": "user", "content": persona_prompt}
                        ],
                        temperature=0.5,
                        max_tokens=600
                    )
                    
                    content = response.choices[0].message.content
                    
                    # Parse the response
                    sections = content.split("KEY POINTS:")
                    model_answer = ""
                    key_points = []
                    reasoning = ""
                    
                    if len(sections) > 1:
                        model_answer = sections[0].replace("MODEL ANSWER:", "").strip()
                        remaining = sections[1].split("REASONING:")
                        if len(remaining) > 1:
                            key_points_text = remaining[0].strip()
                            key_points = [line.strip('- ').strip() for line in key_points_text.split('\n') if line.strip().startswith('-')]
                            reasoning = remaining[1].strip()
                    else:
                        model_answer = content
                        key_points = question.get('key_themes', [])
                    
                    generated_answers[answer_key] = {
                        "question_id": question_id,
                        "persona_id": persona_id,
                        "persona_name": persona['name'],
                        "persona_specialty": persona['specialty'],
                        "persona_practice_setting": persona['practice_setting']['type'],
                        "persona_communication_style": persona['communication_style']['tone'],
                        "persona_priorities": persona['priorities'][:3],
                        "question": question["question"],
                        "category": question["category"],
                        "difficulty": question.get("difficulty", "medium"),
                        "context": question["context"],
                        "estimated_response_time": question.get("estimated_response_time", 60),
                        "model_answer": model_answer,
                        "key_points": key_points if key_points else question.get('key_themes', []),
                        "reasoning": reasoning,
                        "persona_tailored": True,
                        "generated_at": datetime.now().isoformat()
                    }
                    
                    print(f"✓ Generated answer for Q{question_id} + {persona_id}")
                    
                except Exception as e:
                    print(f"✗ Error generating answer for Q{question_id} + {persona_id}: {str(e)}")
    
    # Save all answers to file and S3
    save_data = {
        "answers": generated_answers,
        "metadata": {
            "total_answers": len(generated_answers),
            "generated_at": datetime.now().isoformat()
        }
    }
    
    save_model_answers(save_data)
    
    print(f"\n✅ Complete! Generated {len(generated_answers)} model answers")
    
    return generated_answers


if __name__ == "__main__":
    generate_all_model_answers()