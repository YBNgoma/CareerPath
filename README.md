# Career Guidance System 🎓

A comprehensive web-based career guidance platform specifically designed for Zimbabwe, helping students and professionals make informed career decisions through AI-powered document analysis and interactive assessments.

## ✨ Features

### 🤖 AI-Powered Career Guidance
- **Document-Based Q&A**: Upload PDF career guidance documents and get intelligent answers using RAG (Retrieval-Augmented Generation)
- **Career Assessment**: Interactive questionnaires to match users with suitable career paths
- **Personalized Recommendations**: Tailored career suggestions based on user responses

### 🎯 Zimbabwe-Specific Content
- **Local Career Pathways**: Detailed information for popular careers in Zimbabwe (Doctor, Nurse, Engineer, Teacher)
- **University Information**: Comprehensive database of Zimbabwean universities with application details
- **Local Requirements**: O-Level and A-Level requirements specific to Zimbabwe's education system

### 👤 User Management
- **User Registration & Authentication**: Secure account creation and login system
- **Profile Management**: Track user progress and preferences
- **Chat History**: Persistent conversation history for logged-in users
- **Assessment History**: Track career assessment results over time

### 💬 Interactive Chat Interface
- **Command System**: Quick access to information using slash commands
- **Real-time Responses**: Instant career guidance and pathway information
- **Source Citations**: References to original documents when providing answers

## 🚀 Quick Start

### Prerequisites

Before running the application, you need to have Python installed on your system.

#### Installing Python

**Windows:**
1. Visit [python.org](https://www.python.org/downloads/windows/)
2. Download the latest Python 3.x version
3. Run the installer and **check "Add Python to PATH"**
4. Verify installation: Open Command Prompt and run `python --version`

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python

# Or download from python.org
# Visit https://www.python.org/downloads/macos/
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Linux (CentOS/RHEL/Fedora):**
```bash
sudo yum install python3 python3-pip
# or for newer versions
sudo dnf install python3 python3-pip
```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/career-guidance-system.git
   cd career-guidance-system
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create necessary directories**
   ```bash
   mkdir pdfs
   ```

5. **Add career guidance documents** (Optional)
   - Place your PDF career guidance documents in the `pdfs/` folder
   - The system will automatically process these documents for the Q&A feature

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Open your web browser
   - Navigate to `http://localhost:5001`

## 📁 Project Structure

```
career-guidance-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── career_guidance.db    # SQLite database (auto-created)
├── pdfs/                 # Directory for career guidance PDFs
├── templates/            # HTML templates
│   ├── index.html        # Main chat interface
│   ├── login.html        # User login page
│   ├── register.html     # User registration page
│   ├── profile.html      # User profile page
│   └── assessment.html   # Career assessment page
└── static/              # CSS, JavaScript, and other static files
```

## 🎮 Usage

### Chat Commands

The system supports various slash commands for quick access to information:

| Command | Description |
|---------|-------------|
| `/doctor` | Get detailed pathway for becoming a doctor in Zimbabwe |
| `/nurse` | Get pathway information for nursing career |
| `/engineer` | Get engineering career pathway details |
| `/teacher` | Get teaching career information |
| `/universities` | List all universities in Zimbabwe with details |
| `/history` | View your chat history (requires login) |
| `/help` | Show all available commands |

### Career Assessment

1. Navigate to the Assessment page
2. Answer the interactive questionnaire
3. Get personalized career recommendations
4. View detailed career pathways for top matches

### Document Q&A

1. Add PDF documents to the `pdfs/` folder
2. Ask questions about career guidance in natural language
3. Get AI-powered answers with source citations

## 🔧 Configuration

### Environment Variables

You can customize the application using environment variables:

```bash
# Set a secure secret key for production
export FLASK_SECRET_KEY="your-super-secret-key-here"

# Set Flask environment
export FLASK_ENV=development  # or production
```

### Database

The application uses SQLite by default. The database file `career_guidance.db` is automatically created in the project root directory.

### Adding Custom Content

#### Career Pathways
Edit the `CAREER_PATHWAYS_ZW` dictionary in `app.py` to add or modify career information.

#### Universities
Update the `UNIVERSITIES_ZW` list in `app.py` to add more educational institutions.

#### Assessment Questions
Modify `CAREER_ASSESSMENT_QUESTIONS` in `app.py` to customize the career assessment questionnaire.

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Commit your changes**
   ```bash
   git commit -m "Add some amazing feature"
   ```
5. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines for Python code
- Add comments for complex logic
- Update documentation for new features
- Test your changes thoroughly

## 📋 Requirements

See `requirements.txt` for a complete list of Python dependencies. Key technologies used:

- **Flask**: Web framework
- **LangChain**: AI/ML pipeline for document processing
- **FAISS**: Vector database for document similarity search
- **HuggingFace**: Embeddings and transformers
- **SQLite**: Database for user data and chat history
- **Werkzeug**: Password hashing and security

## 🚀 Deployment

### Production Considerations

1. **Set a secure secret key**
   ```bash
   export FLASK_SECRET_KEY="your-very-long-random-secret-key"
   ```

2. **Use a production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 app:app
   ```

3. **Set up reverse proxy** (nginx recommended)

4. **Enable HTTPS** in production

5. **Regular database backups**

### Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p pdfs

EXPOSE 5001
CMD ["python", "app.py"]
```

## 🐛 Troubleshooting

### Common Issues

**Q: The application won't start**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (Python 3.7+ required)
- Verify virtual environment is activated

**Q: PDF documents aren't being processed**
- Ensure PDFs are placed in the `pdfs/` directory
- Check file permissions and formats
- Review application logs for error messages

**Q: Database errors**
- Delete `career_guidance.db` to reset the database
- Ensure write permissions in the project directory

**Q: Chat responses are generic**
- Add relevant PDF documents to the `pdfs/` folder
- The system uses a placeholder LLM by default - integrate with a real LLM for production use

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Zimbabwean education community
- Inspired by the need for accessible career guidance
- Thanks to all contributors and testers

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com//YBNgoma/CareerPath/issues) page
2. Create a new issue if your problem isn't already reported
3. Provide detailed information about your environment and the issue

---

**Made with ❤️ for Zimbabwe's future leaders**
