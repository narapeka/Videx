# Media File Renaming Tool

A tool for intelligently renaming media files using AI and TMDB API integration.

## Features

- Smart file renaming using Grok AI and TMDB API
- Support for multiple media library directories
- Batch processing of files
- Configurable API settings and proxy options
- User-friendly interface with file preview and selection

## Project Structure

```
aigua/
├── backend/           # FastAPI backend
│   ├── app/          # Application code
│   ├── tests/        # Backend tests
│   └── requirements.txt
├── frontend/         # Vue.js frontend
│   ├── src/         # Source code
│   ├── public/      # Static files
│   └── package.json
└── README.md
```

## Setup

### Backend Setup

1. Create a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend:
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run the development server:
```bash
npm run serve
```

## Configuration

Before using the application, you need to configure:

1. Media library directories
2. Grok API key
3. TMDB API key
4. Proxy settings (if required)

These can be configured through the web interface under the "System Configuration" section.

## API速率限制

应用程序现在使用基于令牌桶算法的API速率限制器来控制API请求速率：

- Grok API: 默认限制为每秒1次请求
- TMDB API: 默认限制为每秒50次请求

当遇到API速率限制错误(429 Too Many Requests)时，系统会自动减半速率并等待适当的时间后重试。
API调用统计信息会在处理完成后显示，包括总调用次数、总耗时、平均耗时、错误次数和速率限制错误次数。 