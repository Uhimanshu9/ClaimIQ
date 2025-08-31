// Dummy data for testing the chat interface
// This will be replaced with real API responses

export const messages = [
  {
    role: "assistant",
    content: "Hello! I'm ready to help you analyze your claim document. Please feel free to ask me any questions about the uploaded PDF.",
    thinking: "I'm initialized and ready to process queries about the uploaded document using vector similarity search and document retrieval techniques."
  }
];

// Example message formats that match your backend response structure
export const exampleMessages = [
  {
    role: "user",
    content: "What is the claim amount mentioned in the document?"
  },
  {
    role: "assistant", 
    content: "Based on the document analysis, the claim amount is $15,000 for property damage.",
    thinking: "I found this information by searching through the document using vector embeddings. The claim amount appears in section 3.2 of the document, specifically mentioning '$15,000 for property damage resulting from the incident on March 15, 2024.' This matches the policy coverage limits outlined in the agreement."
  },
  {
    role: "user",
    content: "Are there any red flags or inconsistencies?"
  },
  {
    role: "assistant",
    content: "I identified 2 potential areas that may require further review regarding timeline discrepancies and witness statements.",
    thinking: "After analyzing the document, I found several areas of concern: 1) Timeline Discrepancy: The incident report states the damage occurred at 2:30 PM, but the initial notification was made at 1:45 PM - 45 minutes before the claimed incident time. 2) Witness Statement Inconsistency: Two witnesses provide conflicting accounts of weather conditions. 3) Prior Claims History: The claimant has filed 3 similar claims in the past 18 months, which may warrant additional investigation."
  }
];

// Mock API response format for reference
export const mockApiResponse = {
  status: "success",
  data: {
    response: "The policy covers up to $50,000 for this type of claim.",
    thinking: "I retrieved this information from the policy document section 4.1 which outlines coverage limits for property damage claims. The specific clause states that coverage extends to $50,000 per incident for property damage caused by natural disasters or accidents, with a $500 deductible."
  }
};