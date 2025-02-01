import json
from datasets import load_dataset, Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForLanguageModeling, Trainer, TrainingArguments

# Replace with your model identifier if needed.
MODEL_NAME = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"

# Load the tokenizer and model.
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

def load_finetune_data(file_path):
    # Expecting a JSON file with a list of {"prompt": "...", "response": "..."} examples.
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Concatenate prompt and response (with a separator) as the training text.
    examples = []
    for ex in data:
        text = ex["prompt"].strip() + "\nAnswer: " + ex["response"].strip() + "\n"
        examples.append({"text": text})
    return Dataset.from_list(examples)

# Load your fine-tuning data.
dataset = load_finetune_data("fine_tune_data.json")

# Tokenize the dataset.
def tokenize_function(example):
    return tokenizer(example["text"], truncation=True, max_length=512)

tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

training_args = TrainingArguments(
    output_dir="./fine_tuned_model",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=500,
    save_total_limit=2,
    prediction_loss_only=True,
    logging_steps=100,
    learning_rate=5e-5,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)

trainer.train()
trainer.save_model("./fine_tuned_model")
tokenizer.save_pretrained("./fine_tuned_model")