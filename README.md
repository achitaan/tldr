# TLDR: A Guide to Instructions

## Inspiration
The impetus for **TLDR: A Guide to Instructions** began when one of our team members’ grandmother accidentally took the wrong medication. This unfortunate event was due to cluttered and unclear labeling on her medication bottle. We wanted to create a solution that prevents such incidents by enabling users—especially those with visual impairments or anyone short on time—to quickly understand essential medication information without sifting through extensive text.

## Problem Statement
Reading and comprehending complex medication labels or long text blocks can be time-consuming and prone to errors. Individuals with visual impairments are disproportionately affected, as standard labels often do not provide sufficient clarity or accessibility. **TLDR: A Guide to Instructions** addresses these challenges by offering a streamlined approach to extracting and communicating critical information, drastically reducing the chance of misinterpretation.

## Project Overview
**TLDR: A Guide to Instructions** is a full-stack web application that integrates:

- **Computer Vision & OCR**  
  Uses a custom-trained **YOLOv8** model to detect objects (e.g., medication bottles) in real time, and applies **Tesseract OCR** to extract text from images.

- **Text Summarization & Q&A**  
  Leverages **OpenAI API** calls to parse and summarize extracted text, and provides an interactive question-and-answer system for further clarification.

- **Audio-based Input/Output**  
  Employs **speech recognition** for user input and **GTTS** for text-to-speech output, facilitating hands-free and accessible interactions.

- **Optimized Image Preprocessing**  
  Uses **OpenCV** to boost text recognition accuracy by enhancing image clarity through various preprocessing techniques.

- **Robust Data Handling**  
  Implements a **MySQL** database to log user queries and responses, and a **RESTful** API to maintain conversational memory.

## Key Highlights (Derived from Development Experience)
- Developed a **React** and **Django** full-stack application to improve medication accessibility for visually impaired users, featuring audio-based interaction.
- Enhanced text recognition performance by optimizing image preprocessing with **OpenCV**.
- Implemented a **MySQL** database and a **RESTful** API to manage conversational history, integrating an auditory Q&A system using **OpenAI API** calls.

## How It Works
1. **Capture**  
   The user initiates a real-time camera feed. When ready, the system captures a frame containing the medication label or any block of text.

2. **Detection & Recognition**  
   - A custom-trained **YOLOv8** model identifies and tracks the object of interest.  
   - **Tesseract OCR** recognizes text in the identified region.  
   - **OpenCV**-powered preprocessing ensures higher legibility and recognition accuracy.

3. **Summarization & Query**  
   The extracted text is summarized using **OpenAI**, presenting key information most relevant to the user.  
   The user can then pose follow-up questions to clarify any details.

4. **Audio Interface**  
   - **GTTS** converts summarized text or chatbot answers into speech output.  
   - **Speech recognition** allows for verbal questions, supporting accessibility for users with visual impairments and those who prefer hands-free interaction.

## Challenges
- **Complex Integrations**: Combining multiple technologies (YOLOv8, Tesseract, OpenCV, GTTS, and external APIs) into a cohesive system required precise coordination and debugging.  
- **Optimization**: Fine-tuning OCR and detection models to ensure consistent performance under varying conditions (e.g., lighting, image quality) was challenging.  
- **Conversational Memory**: Maintaining context for multiple user interactions involved building a robust system to handle stateful dialogues.

## Accomplishments
- Successfully integrated computer vision and OCR to handle real-world scenarios.  
- Completed a full-stack deployment within a tight timeline.  
- Created an accessible, user-friendly solution that promotes safer, quicker reading of medication labels and other long texts.

## What We Learned
- **Tesseract Optimization**: Discovered various image preprocessing techniques to substantially increase OCR accuracy.  
- **Generative AI Integration**: Gained experience in leveraging OpenAI models for text summarization and contextual understanding.  
- **Audio I/O Implementation**: Developed familiarity with speech recognition and text-to-speech for improved user interaction.

## Next Steps
1. **Mobile Platform**: Expand to a mobile app for rapid scanning and reading on-the-go.  
2. **Improved Accuracy**: Further train or refine our models to enhance detection and comprehension reliability.  
3. **Extended Use Cases**: Tailor TLDR for textbooks, legal documents, or any scenario where quick summarization is beneficial.

---

### Getting Started

1. **Clone the Repository**
   ```bash
   git clone https://github.com/YourUsername/TLDR-Guide-to-Instructions.git
   
  

Install Dependencies
In the project directory, install the Python and Node.js dependencies:
```
cd TLDR-Guide-to-Instructions
pip install -r requirements.txt
npm install
```

Create a .env file for your OpenAI API key and other environment variables.
Set up your MySQL credentials for the database.
Run the Application

Backend (Django):
bash
```
python manage.py runserver
```
python manage.py runserver
Frontend (React):
```
npm start
```
