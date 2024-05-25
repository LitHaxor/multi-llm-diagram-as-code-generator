# UML Diagram Validator


## Installation

### Python venv

```
python3 -m venv venv
source venv/bin/activate
```

### Install requirements

```
pip install -r requirements.txt
```

### Install Redis

#### Ubuntu

```
sudo apt update
sudo apt install redis-server
```

**Start Redis**

```
sudo systemctl start redis
```

**Check Redis status**

```
sudo systemctl status redis
```


##### MacOS

```
brew install redis
```

**Start Redis**

```
brew services start redis
```

**Check Redis status**

```

brew services list
```

#### Windows

[Download Redis]()

**Start Redis**

```
redis-server
```



## Running the applications

```
uvicorn main:app --reload
```


## Workers

### Claude worker

```
celery -A workers.claude_worker worker --loglevel=info
```

### Gemini worker

```
celery -A workers.gemini_worker worker --loglevel=info
```