import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.tools import tool
from langchain_core.tools.retriever import create_retriever_tool
from langchain_community.vectorstores import FAISS
from database import fetch_student_performance_summary
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

load_dotenv()

# --- STEP 1: Behavioral Tool (XAMPP) ---
@tool
def get_student_analytics(reg_number: str):
    """Retrieves test scores and study time to personalize tutoring."""
    data = fetch_student_performance_summary(reg_number)
    return str(data)

# --- STEP 2: Knowledge Tool (PDF) ---
tools = [get_student_analytics]

if os.path.exists("faiss_learning_index"):
    # This MUST match vector_store.py
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    
    vector_db = FAISS.load_local(
        "faiss_learning_index", 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    
    retriever_tool = create_retriever_tool(
        vector_db.as_retriever(),
        "search_course_material",
        "Searches and retrieves detailed information from course materials."
    )
    tools.append(retriever_tool)

# --- STEP 3: Initialize Gemini Brain ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

def _extract_text(content):
    """Extract plain text from LLM response content, handling both string and list formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)

# Custom Agent Executor to bypass deprecated legacy langchain.agents packages
class CustomAgentExecutor:
    def __init__(self, llm, tools, system_prompt):
        self.llm = llm.bind_tools(tools) if tools else llm
        self.tools = tools
        self.system_prompt = system_prompt
        
    def invoke(self, inputs, **kwargs):
        input_str = inputs.get("input", "")
        history = inputs.get("chat_history", [])
        
        # 1. Format initial messages
        messages = [
            SystemMessage(content=self.system_prompt)
        ]
        
        # 2. Add chat history safely
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
            elif isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                messages.append(msg)
                
        # 3. Add current human input
        messages.append(HumanMessage(content=input_str))
        
        # 4. Invoke model
        response = self.llm.invoke(messages)
        
        # 5. Handle tool call loop
        iterations = 0
        max_iterations = 5
        while response.tool_calls and iterations < max_iterations:
            messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                target_tool = next((t for t in self.tools if t.name == tool_name), None)
                if target_tool:
                    try:
                        tool_output = target_tool.invoke(tool_args)
                    except Exception as e:
                        tool_output = f"Error executing tool: {e}"
                else:
                    tool_output = f"Error: Tool '{tool_name}' not found."
                    
                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))
                
            response = self.llm.invoke(messages)
            iterations += 1
            
        return {"output": _extract_text(response.content)}

system_prompt = (
    "You are a Gemini-powered AI Tutor. Always check student metrics first using get_student_analytics. "
    "Answer conceptual questions using the search_course_material tool. "
    "If exam scores are low, encourage the student to focus on weak areas and suggest improvement steps."
)

agent_executor = CustomAgentExecutor(llm, tools, system_prompt)



def generate_student_report(reg_number, threshold):
    perf = fetch_student_performance_summary(reg_number)
    
    prompt = f"""
    You are an AI Tutor Assistant for a teacher.
    The student has an average quiz score of {perf['avg_score']}% and a total reading time of {perf['total_time']} minutes.
    The teacher's minimum performance threshold is {threshold}%.
    
    Please write a short, detailed report for the teacher on how the student is doing.
    Identify if they are underperforming (below the {threshold}% threshold) and recommend steps to improve.
    Keep it concise but informative.
    """
    
    try:
        response = llm.invoke(prompt)
        return _extract_text(response.content)
    except Exception as e:
        # High-Fidelity local rules-based fallback diagnostic report
        avg_score = perf['avg_score']
        total_time = perf['total_time']
        
        if avg_score < threshold:
            status_text = (
                f"🚨 UNDERPERFORMING: The student's average exam score of {avg_score}% falls below your "
                f"set performance threshold of {threshold}%."
            )
            rec_text = (
                f"1. **Remedial Action Needed:** Recommend scheduling structured revision slots focusing on "
                f"missed concepts.\n"
                f"2. **Increase Engagement:** The current logged reading time is {total_time} minutes. Suggest "
                f"encouraging the student to spend more time with the reference materials.\n"
                f"3. **Targeted Quizzing:** Assign modular practice quizzes to build confidence before the final exam."
            )
        else:
            status_text = (
                f"✅ SATISFACTORY: The student's average exam score of {avg_score}% is meeting or exceeding your "
                f"set performance threshold of {threshold}%."
            )
            rec_text = (
                f"1. **Advance Curriculum:** Encourage the student to explore more advanced reference materials.\n"
                f"2. **Maintain Consistency:** The student has already logged {total_time} minutes of active study time. "
                f"Recommend maintaining this steady learning velocity.\n"
                f"3. **Peer Mentorship:** Suggest inviting them to participate in peer tutor discussions."
            )
            
        fallback_report = f"""⚠️ **[API Quota Exhausted - Local High-Fidelity Diagnostics]**

### 👩‍🏫 STUDENT PERFORMANCE DIAGNOSTIC REPORT
* **Student ID Registration:** `{reg_number}`
* **Track Average Exam Score:** `{avg_score}%` *(Syllabus Threshold: {threshold}%)*
* **Total Study Velocity:** `{total_time} minutes`

---

#### 📊 ACADEMIC STANDING STATUS:
{status_text}

#### 📈 RECOMMENDED IMPROVEMENT WORKSPACE:
{rec_text}
"""
        return fallback_report

def generate_dynamic_quiz(subject):
    if not os.path.exists("faiss_learning_index"):
        return get_local_fallback_quiz(subject)
    
    try:
        retriever = vector_db.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(subject)
        context = "\n\n".join([doc.page_content for doc in docs])
    except Exception:
        # If retriever fails, proceed to local fallback quiz
        return get_local_fallback_quiz(subject)
    
    if not context.strip():
        return get_local_fallback_quiz(subject)
        
    prompt = f"""
    You are an expert tutor. Based ONLY on the following course material context, generate a 2-question multiple choice quiz about the subject "{subject}".
    
    Context:
    {context}
    
    Format the output strictly as a JSON list of objects, like this:
    [
      {{
        "question": "The question text?",
        "options": ["Option A", "Option B", "Option C"],
        "answer": "Option B"
      }},
      ...
    ]
    Make sure exactly one option is exactly the same as the "answer".
    Do not output any other text, just the JSON array.
    """
    
    try:
        response = llm.invoke(prompt)
        import json
        text = _extract_text(response.content).strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Quiz generation API failed, falling back to local database: {e}")
        return get_local_fallback_quiz(subject)

def get_local_fallback_quiz(subject):
    fallback_quizzes = {
        "Literature": [
            {
                "question": "Which of the following is considered a primary element of narrative structure?",
                "options": ["Chronological pacing", "Plot development and conflict", "Setting descriptions only"],
                "answer": "Plot development and conflict"
            },
            {
                "question": "What is the primary function of figurative language in creative writing?",
                "options": ["To extend text lengths", "To convey deeper metaphorical meanings", "To replace grammatical rules"],
                "answer": "To convey deeper metaphorical meanings"
            }
        ],
        "Physics": [
            {
                "question": "What does Newton's Second Law of Motion state?",
                "options": ["Energy is conserved in closed systems", "Force equals mass times acceleration (F=ma)", "Actions have equal and opposite reactions"],
                "answer": "Force equals mass times acceleration (F=ma)"
            },
            {
                "question": "Which of the following forces opposes relative motion between two contact surfaces?",
                "options": ["Gravitational force", "Frictional force", "Centripetal acceleration"],
                "answer": "Frictional force"
            }
        ],
        "Chemistry": [
            {
                "question": "What is the primary subatomic particle responsible for forming chemical bonds?",
                "options": ["Neutrons in the core", "Protons in the nucleus", "Valence electrons in the outer shell"],
                "answer": "Valence electrons in the outer shell"
            },
            {
                "question": "Which of the following describes an exothermic chemical reaction?",
                "options": ["A reaction that releases heat energy into surroundings", "A reaction that absorbs thermal energy", "A reaction that maintains absolute temperature"],
                "answer": "A reaction that releases heat energy into surroundings"
            }
        ],
        "Math": [
            {
                "question": "What is the value of x if 3x + 7 = 22?",
                "options": ["x = 5", "x = 6", "x = 4"],
                "answer": "x = 5"
            },
            {
                "question": "Which of the following represents the derivative of f(x) = x^2 in calculus?",
                "options": ["f'(x) = 2x", "f'(x) = x", "f'(x) = 2"],
                "answer": "f'(x) = 2x"
            }
        ]
    }
    # Match subject name (case-insensitive) or return a default Literature quiz
    subject_key = next((k for k in fallback_quizzes.keys() if k.lower() == str(subject).lower()), "Literature")
    return fallback_quizzes[subject_key]