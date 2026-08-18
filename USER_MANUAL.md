# DocuTrace AI - User Manual

Welcome to **DocuTrace AI**, a state-of-the-art multilingual corporate document search and question-answering assistant, built and designed by **[SS Labz](https://ss-labz.pages.dev/)**.

DocuTrace AI utilizes hybrid semantic retrieval, layout table parsing, query translation, parent-child document chunking, conversational chat history memory, role-based access security, and vision-language processing to extract grounded answers from corporate documents.

---

## 1. Getting Started

### Accessing the Dashboard
1. Ensure the database container and FastAPI server are running.
2. Open your web browser and navigate to:
   👉 **[http://localhost:8008/](http://localhost:8008/)**
3. You will be greeted by the dark-mode glassmorphic dashboard interface.

---

## 2. Ingesting Corporate Policies & Visual RAG

To ask questions about a policy, you must first ingest the document into the system.

1. **Select a File**:
   - Drag and drop any corporate PDF policy document directly into the upload area in the left sidebar.
2. **Assign Department & User Role**:
   - Select the target department context (e.g. *Human Resources*, *Finance*, *Operations*, or *Security*) from the dropdown.
   - Select the active Simulated User Role (e.g. *regular_user*, *admin*) to restrict/permit retrieval based on access rights.
3. **Multi-Modal / Visual Extraction (Visual RAG)**:
   - Click the **"Upload Policy"** button.
   - If a page has diagrams, drawings, charts, or is completely scanned (zero characters):
     - The parser automatically renders the page into an image and sends it to the OpenAI Vision-Language API (`gpt-4o-mini`).
     - The detailed textual summary of the visual contents (labels, figures, workflows) is generated and appended to the chunks, making drawings and charts fully searchable.

---

## 3. Querying & Conversational Memory

DocuTrace AI allows you to query policy databases using natural conversational language.

1. **Ask Initial Question**:
   - Type your question in the chat input box at the bottom-right (e.g. `"What is the visual model code on the Technical Chart?"`).
   - The assistant returns the grounded answer with source citations.
2. **Ask Follow-up Questions**:
   - You can ask follow-up questions referencing previous answers without repeating context (e.g. `"Is the basement safe during it?"`).
   - The assistant automatically re-contextualizes the query before search.
3. **Start a New Chat**:
   - Click the **"New Chat"** button inside the header bar next to the badges to start a fresh topic.

---

## 4. Viewing Citations

To ensure transparency and absolute truthfulness, DocuTrace AI includes an interactive citations panel:

1. Locate the **"Show Citations (N)"** button directly underneath the assistant's chat bubble response.
2. Click the button to expand the source card list.
3. For each source card, you can view:
   - **Document Info**: Source filename and page number.
   - **Relevance Score**: The computed Cross-Encoder score (or RRF score) indicating exact contextual match alignment.
   - **Exact Matching Snippet**: The precise child chunk segment where the keyword/concept matched.

---

## About SS Labz

**DocuTrace AI** is proudly developed by **[SS Labz](https://ss-labz.pages.dev/)**, dedicated to creating intelligent, localized enterprise solutions. Visit our website at [https://ss-labz.pages.dev/](https://ss-labz.pages.dev/) to discover more systems and products.
