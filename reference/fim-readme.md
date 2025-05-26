# Fim
(*fim*)

## Overview

Fill-in-the-middle API.

### Available Operations

* [stream](#stream) - Stream fim completion
* [create](#create) - Fim Completion

## stream

Mistral AI provides the ability to stream responses back to a client in order to allow partial results for certain requests. Tokens will be sent as data-only server-sent events as they become available, with the stream terminated by a data: [DONE] message. Otherwise, the server will hold the request open until the timeout or until completion, with the response containing the full result as JSON.

### Example Usage

```python
from mistralai_gcp import MistralGCP
import os

s = MistralGCP()


res = s.fim.stream(prompt="def", model="codestral-2405", suffix="return a+b")

if res is not None:
    for event in res:
        # handle event
        print(event)

```

### Parameters

| Parameter     | Type                                                                                              | Required           | Description                                                                                                                                                                                                                                                   | Example        |
| ------------- | ------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| `prompt`      | *str*                                                                                             | :heavy_check_mark: | The text/code to complete.                                                                                                                                                                                                                                    | def            |
| `model`       | *OptionalNullable[str]*                                                                           | :heavy_minus_sign: | ID of the model to use. Only compatible for now with:<br/>  - `codestral-2405`<br/>  - `codestral-latest`                                                                                                                                                     | codestral-2405 |
| `temperature` | *Optional[float]*                                                                                 | :heavy_minus_sign: | What sampling temperature to use, between 0.0 and 1.0. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. We generally recommend altering this or `top_p` but not both.        |                |
| `top_p`       | *Optional[float]*                                                                                 | :heavy_minus_sign: | Nucleus sampling, where the model considers the results of the tokens with `top_p` probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered. We generally recommend altering this or `temperature` but not both. |                |
| `max_tokens`  | *OptionalNullable[int]*                                                                           | :heavy_minus_sign: | The maximum number of tokens to generate in the completion. The token count of your prompt plus `max_tokens` cannot exceed the model's context length.                                                                                                        |                |
| `min_tokens`  | *OptionalNullable[int]*                                                                           | :heavy_minus_sign: | The minimum number of tokens to generate in the completion.                                                                                                                                                                                                   |                |
| `stream`      | *Optional[bool]*                                                                                  | :heavy_minus_sign: | N/A                                                                                                                                                                                                                                                           |                |
| `stop`        | [Optional[models.FIMCompletionStreamRequestStop]](../../models/fimcompletionstreamrequeststop.md) | :heavy_minus_sign: | Stop generation if this token is detected. Or if one of these tokens is detected when providing an array                                                                                                                                                      |                |
| `random_seed` | *OptionalNullable[int]*                                                                           | :heavy_minus_sign: | The seed to use for random sampling. If set, different calls will generate deterministic results.                                                                                                                                                             |                |
| `suffix`      | *OptionalNullable[str]*                                                                           | :heavy_minus_sign: | Optional text/code that adds more context for the model. When given a `prompt` and a `suffix` the model will fill what is between them. When `suffix` is not provided, the model will simply execute completion starting with `prompt`.                       | return a+b     |
| `retries`     | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                  | :heavy_minus_sign: | Configuration to override the default retry behavior of the client.                                                                                                                                                                                           |                |


### Response

**[Union[Generator[models.CompletionEvent, None, None], AsyncGenerator[models.CompletionEvent, None]]](../../models/.md)**
### Errors

| Error Object    | Status Code | Content Type |
| --------------- | ----------- | ------------ |
| models.SDKError | 4xx-5xx     | */*          |

## create

FIM completion.

### Example Usage

```python
from mistralai_gcp import MistralGCP
import os

s = MistralGCP()


res = s.fim.complete(prompt="def", model="codestral-2405", suffix="return a+b")

if res is not None:
    # handle response
    pass

```

### Parameters

| Parameter     | Type                                                                                  | Required           | Description                                                                                                                                                                                                                                                                                                                        | Example        |
| ------------- | ------------------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| `prompt`      | *str*                                                                                 | :heavy_check_mark: | The text/code to complete.                                                                                                                                                                                                                                                                                                         | def            |
| `model`       | *OptionalNullable[str]*                                                               | :heavy_minus_sign: | ID of the model to use. Only compatible for now with:<br/>  - `codestral-2405`<br/>  - `codestral-latest`                                                                                                                                                                                                                          | codestral-2405 |
| `temperature` | *Optional[float]*                                                                     | :heavy_minus_sign: | What sampling temperature to use, between 0.0 and 1.0. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. We generally recommend altering this or `top_p` but not both.                                                                             |                |
| `top_p`       | *Optional[float]*                                                                     | :heavy_minus_sign: | Nucleus sampling, where the model considers the results of the tokens with `top_p` probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered. We generally recommend altering this or `temperature` but not both.                                                                      |                |
| `max_tokens`  | *OptionalNullable[int]*                                                               | :heavy_minus_sign: | The maximum number of tokens to generate in the completion. The token count of your prompt plus `max_tokens` cannot exceed the model's context length.                                                                                                                                                                             |                |
| `min_tokens`  | *OptionalNullable[int]*                                                               | :heavy_minus_sign: | The minimum number of tokens to generate in the completion.                                                                                                                                                                                                                                                                        |                |
| `stream`      | *Optional[bool]*                                                                      | :heavy_minus_sign: | Whether to stream back partial progress. If set, tokens will be sent as data-only server-side events as they become available, with the stream terminated by a data: [DONE] message. Otherwise, the server will hold the request open until the timeout or until completion, with the response containing the full result as JSON. |                |
| `stop`        | [Optional[models.FIMCompletionRequestStop]](../../models/fimcompletionrequeststop.md) | :heavy_minus_sign: | Stop generation if this token is detected. Or if one of these tokens is detected when providing an array                                                                                                                                                                                                                           |                |
| `random_seed` | *OptionalNullable[int]*                                                               | :heavy_minus_sign: | The seed to use for random sampling. If set, different calls will generate deterministic results.                                                                                                                                                                                                                                  |                |
| `suffix`      | *OptionalNullable[str]*                                                               | :heavy_minus_sign: | Optional text/code that adds more context for the model. When given a `prompt` and a `suffix` the model will fill what is between them. When `suffix` is not provided, the model will simply execute completion starting with `prompt`.                                                                                            | return a+b     |
| `retries`     | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                      | :heavy_minus_sign: | Configuration to override the default retry behavior of the client.                                                                                                                                                                                                                                                                |                |


### Response

**[models.FIMCompletionResponse](../../models/fimcompletionresponse.md)**
### Errors

| Error Object               | Status Code | Content Type     |
| -------------------------- | ----------- | ---------------- |
| models.HTTPValidationError | 422         | application/json |
| models.SDKError            | 4xx-5xx     | */*              |
