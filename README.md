# serving-stack

The one system this course builds. Your team creates this repository once from
the template, and every lab from week 2 to graduation is a change to it. There
is no week where you start again.

## What is here

```
app/        empty. Your service goes here, starting week 2 day 2
docs/       the API contract the Agentic AI cohort integrates against
scripts/    verify-env.sh, which checks your machine against what the labs need
PINS.md     every version this course depends on
setup.md    how to work in this repository
```

That is the whole repository, and the shortness of that list is the point. You
are not given a finished system to read. You build one, a day at a time, and by
week 6 another cohort's agents are calling it.

## What you add, and when

| Week | Day | What you add                                                |
| ---- | --- | ----------------------------------------------------------- |
| 2    | Mon | `app/` behind an OpenAI-compatible `/v1` on CPU             |
| 2    | Tue | `Dockerfile`, and your image on Docker Hub                  |
| 2    | Wed | `Dockerfile.gpu`, the same code on a GPU                    |
| 2    | Thu | `compose.yaml`, the stack described rather than run by hand |
| 3    | Thu | `bench/`, the harness that measures all of it               |

Each one is a lab, and each one starts from files that day hands you. Lab
instructions, decks and quizzes are on the course Drive, one folder per week.
This repository is your code.

## Start here

```bash
./scripts/verify-env.sh     # checks your machine, writes verify-env-report.json
```

Then read `setup.md`. It is short, and it covers the two things that go wrong:
committing a key, and committing a model.

## Build

```bash
docker build -t mindg/ai-serve-stack .
```

## Run with local mount storage

- we can delete --rm and use -d to run the container in the background
- change **/home/nassir/aidc-bootcamp/models/Qwen2.5-0.5B-Instruct** to you model path
- change **mindg/ai-serve-stack** to your image name

```bash
docker run --rm -p 8000:8000 --env-file aidc-nassir-serving-stack/.env  --mount type=bind,source=/home/nassir/aidc-bootcamp/models/Qwen2.5-0.5B-Instruct,target=/model,readonly mindg/ai-serve-stack
```

## Run with named volume storage

- we can delete --rm and use -d to run the container in the background
- change **ai-models** to your volume name 
- change **mindg/ai-serve-stack** to your image name

```bash
docker run --rm -p 8000:8000 --env-file aidc-nassir-serving-stack/.env -v ai-models:/app/.cache/huggingface mindg/ai-serve-stack
```
### last update:
### API Authentication

The `/v1/chat/completions` route requires API authentication.

Include your API key in the `Authorization` header when making requests.

#### Example

```bash
curl -H "x-api-key: 86937aa022c3a035556bea0b8d5d2ec8" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/v1/chat/completions \
  -d '{
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "messages": [
      {
        "role": "user",
        "content": "Hello"
      }
    ],
    "max_tokens": 50
  }'
