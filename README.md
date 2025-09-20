# Indian Law AI Portal

An **AI-powered legal query assistant** that answers questions about Indian laws using **RAG (Retrieval-Augmented Generation)** and specialized agentic AI frameworks.

This project is designed to help users get **reliable, explainable, and up-to-date** answers about Indian legal matters by leveraging **official government books**, converting them into machine-readable embeddings, and using intelligent agents for domain-specific reasoning.

---

## Features

* **Agentic AI Architecture**

  * Specialized AI agents for different legal domains (e.g., Criminal Law, Civil Law, Taxation, etc.)
  * Automatic agent selection based on user query.

* **RAG (Retrieval-Augmented Generation)**

  * Converts official Indian law books into chunks (section/paragraph-based).
  * Creates embeddings for semantic search.
  * Uses **RAG Fusion** with `n=3` to reformulate queries and improve retrieval coverage.

* **Context-Aware Query Resolution**

  * Retrieves **Top 10 most relevant chunks** for each user query.
  * Passes retrieved context + query to LLM for final, human-readable answer.

* **Scalable & Extensible**

  * Easy to add new books, domains, or specialized agents.
  * Designed to be API-first for use in portals, chatbots, or enterprise systems.

---

## Architecture

```mermaid
flowchart TD
    A[User Query] --> B[Query Pre-Processing]
    B --> C[RAG Fusion (n=3 reformulations)]
    C --> D[Vector Search - Top 10 Matches]
    D --> E[Select Domain-Specific Agent]
    E --> F[LLM + Retrieved Context]
    F --> G[Final Answer to User]
```

---

## Data Pipeline

1. **Book Preprocessing**

   * Extract text from official government law books.
   * Segment into **sections/paragraphs** as chunks.
   * Clean & normalize text (remove formatting, OCR errors).

2. **Embedding Generation**

   * Convert chunks into vector embeddings using selected embedding model.
   * Store embeddings in vector database (e.g., Pinecone, FAISS, Weaviate).

3. **Query Handling**

   * Accept user query.
   * Apply **RAG Fusion** to generate 3 reformulated versions of the query.
   * Perform similarity search to retrieve top 10 chunks per query.
   * Pass to **domain-specific agent** for reasoning.

---

## Tech Stack

| Component           | Technology/Choice                                                                       |
| ------------------- | --------------------------------------------------------------------------------------- |
| **AI Framework**    | Google AI SDK (Vertex AI / Generative AI SDK)                                           |
| **Embedding Model** | (Choose best performing, e.g., `text-embedding-004` or OpenAI `text-embedding-3-large`) |
| **Vector Database** | FAISS / Pinecone / Weaviate                                                             |
| **LLM**             | Google Gemini / OpenAI GPT                                                              |
| **RAG Technique**   | RAG Fusion (n=3)                                                                        |
| **Backend**         | Python (FastAPI / Flask)                                                                |
| **Frontend**        | React / Next.js (Optional Portal UI)                                                    |

---

## Example Flow

**User Query:**

> "What is the punishment for theft under IPC?"

**System Flow:**

1. Reformulates into 3 queries:

   * "Punishment for theft in Indian Penal Code"
   * "IPC section for theft penalty"
   * "Legal consequences of theft under Indian law"

2. Retrieves **top 10 most relevant chunks** from IPC book.

3. Selects **Criminal Law Agent**.

4. Passes chunks + user query to LLM.

5. Returns structured answer with section references.

---

## Advantages

* Ensures **accuracy** by using official government sources.
* Improves **recall** with query reformulation.
* Reduces **hallucination risk** by grounding answers in retrieved text.
* Modular & **domain-extensible** (e.g., can add GST laws, labor laws later).

---

## Future Enhancements

* 🔎 **Citation Mode** – Provide clickable references to original sections.
* 🧾 **Case Law Integration** – Add Supreme Court/High Court judgements.
* 🗣️ **Multilingual Support** – Hindi + regional language queries.
* 📲 **WhatsApp/Telegram Bot** – Allow users to query via messaging apps.

---

## 🛠️ Setup

### 1️⃣ Clone Repo

```bash
git clone https://github.com/your-org/indian-law-portal.git
cd indian-law-portal
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Configure Environment

Create `.env` file with:

```bash
GOOGLE_API_KEY=your_google_api_key
VECTOR_DB_URL=your_vector_db_endpoint
LLM_MODEL=gemini-1.5-pro
```

### 4️⃣ Run Application

```bash
python app.py
```

Visit **[http://localhost:8000](http://localhost:8000)** to access the portal.

---

## Contributing

Contributions are welcome!

* Open an issue for bugs, improvements, or new feature requests.
* Fork repo & submit a PR for review.

---

## License

MIT License – Free to use and modify with attribution.

---
