import ollama


def get_model(model_name):
    local_models = ollama.list()

    for model in local_models.models:
        if model.model == model_name:
            return model

    try:
        return ollama.pull(model_name)
    except Exception as e:
        print("Model doesn't exist")
        raise e

if __name__ == "__main__":
    get_model("llama3.2:latest")