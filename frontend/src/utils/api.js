// API functions for backend integration

// Base API URL - FastAPI backend
const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

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

// Send chat message and get AI response
export async function queryPDF(query, collectionName = "pdf_collection") {
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
        collection_name: collectionName 
      }),
    });

    if (!response.ok) {
      throw new Error(`Query request failed: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.status === "success") {
      // Format response to match frontend expectations
      return {
        response: result.data.response || result.data,
        thinking: result.data.thinking || "Analysis completed using vector similarity search and document retrieval.",
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
export async function askQuestion(query, fileId) {
  // Note: Your backend doesn't use fileId in the query endpoint
  // It uses collection_name instead, so we'll use the default collection
  return await queryPDF(query);
}