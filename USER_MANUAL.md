# DocuTrace AI - User Manual

Welcome to **DocuTrace AI**, a state-of-the-art multilingual corporate document search and question-answering assistant, built and designed by **[SS Labz](https://ss-labz.pages.dev/)**.

DocuTrace AI utilizes hybrid semantic retrieval, layout table parsing, query translation, parent-child document chunking, conversational chat history memory, role-based access security, vision-language processing, advanced metadata search filters, and automatic Markdown report generation to extract grounded answers.

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
   - Page graphics, flowcharts, or drawings are automatically described by the vision engine and indexed.

---

## 3. Advanced Search & Scope Filters

DocuTrace AI allows you to narrow your search to target specific files or ingestion periods:

1. **Filter by File**:
   - The dropdown list dynamically loads the filename of every successfully ingested document.
   - Select a specific filename to restrict retrieval matching to that document only.
2. **Filter by Date**:
   - Select from the Date range filter to search documents indexed within the last 24 hours, 7 days, 30 days, or any time.

---

## 4. Querying & Conversational Memory

1. **Ask Initial Question**:
   - Type your question in the chat input box at the bottom-right (e.g. `"What is the annual leave carryover policy?"`).
   - The assistant returns the grounded answer with source citations.
2. **Ask Follow-up Questions**:
   - You can ask follow-up questions referencing previous answers without repeating context (e.g. `"How do I request an exception to it?"`).
3. **Start a New Chat**:
   - Click the **"New Chat"** button inside the header bar to clear visual feeds and start a fresh conversation session.

---

## 5. Exporting Chat Reports

DocuTrace AI enables users to download comprehensive conversational transcripts directly:

1. Initiate a query to start an active conversation thread.
2. Locate the green glowing **"Export Report"** button inside the dashboard header.
3. Click **"Export Report"**.
4. The system will compile the chat logs and save the downloadable Markdown report file (`chat_report_{session_id}.md`) to your local Downloads directory.
5. The exported Markdown contains:
   - Metadata stamps (Date, Session ID, SS Labz credentials).
   - Entire transcript blocks (User and Assistant dialogues).
   - Citation references lists (Document name, Page number, relevance score, matching content snippet) for every assistant response.

---

## About SS Labz

**DocuTrace AI** is proudly developed by **[SS Labz](https://ss-labz.pages.dev/)**, dedicated to creating intelligent, localized enterprise solutions. Visit our website at [https://ss-labz.pages.dev/](https://ss-labz.pages.dev/) to discover more systems and products.
