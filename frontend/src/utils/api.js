// API functions for backend integration

// Base API URL - FastAPI backend
// Vite exposes browser environment variables through import.meta.env.
// Use VITE_API_URL when the API is hosted elsewhere.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Upload file to backend
export async function uploadFile(file) {
  // 🔹 Backend endpoint: POST /upload
  // Expected request: FormData with file
  // Expected response: { file_id: string }
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    return {
      fileId: data.file_id,
      fileName: file.name,
      success: true
    };
  } catch (error) {
    console.error('File upload error:', error);
    throw error;
  }
}

export async function getFileStatus(fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/status`);
  if (!response.ok) {
    throw new Error(`Couldn't check indexing status: ${response.statusText}`);
  }
  return response.json();
}

export async function getDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents`);
  if (!response.ok) throw new Error("Couldn't load knowledge base documents.");
  return response.json();
}

export async function getChatHistory() {
  const response = await fetch(`${API_BASE_URL}/chat-history`);
  if (!response.ok) throw new Error("Couldn't load chat history.");
  return response.json();
}

export async function saveChatHistory(conversation) {
  const response = await fetch(`${API_BASE_URL}/chat-history/${conversation.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: conversation.id,
      title: conversation.title,
      document_name: conversation.documentName,
      file_id: conversation.fileId,
      provider: conversation.provider,
      messages: conversation.messages,
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Couldn't save chat history.");
  }
  return response.json();
}

export async function cancelFileProcessing(fileId) {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/cancel`, { method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Couldn't cancel document indexing.");
  }
  return response.json();
}

// Send chat message and get AI response
export async function queryPDF(query, provider = "gemini") {
  // 🔹 Backend endpoint: POST /query
  // Expected request: { query: string, collection_name: string }
  // Expected response: { 
  //   status: "success",
  //   data: {
  //     response: string,     // Brief answer
  //     thinking: string      // Detailed reasoning (if available)
  //   }
  // }
  
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json" 
      },
      body: JSON.stringify({ 
        query, 
        provider,
      }),
    });

    if (!response.ok) {
      throw new Error(`Query request failed: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.status === "success") {
      // Format response to match frontend expectations
      return {
        response: result.data.final_answer || "No answer was returned.",
        thinking: `Answered with ${result.data.provider || provider}${result.data.model ? ` (${result.data.model})` : ""} using retrieved document chunks.`,
        success: true
      };
    } else {
      throw new Error("Query failed on server");
    }
  } catch (error) {
    console.error('Query request error:', error);
    throw error;
  }
}

// Check backend health
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/`);
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Health check error:', error);
    throw error;
  }
}

// Legacy function name for backward compatibility
export async function askQuestion(query) {
  // Note: Your backend doesn't use fileId in the query endpoint
  // It uses collection_name instead, so we'll use the default collection
  return await queryPDF(query);
}
