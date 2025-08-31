import React, { useState } from "react";
import { uploadFile } from "../utils/api";

const FileUpload = ({ onFileSelect }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const handleFileSelect = async (file) => {
    if (!file) return;
    
    if (file.type !== "application/pdf") {
      setUploadError("Please select a PDF file");
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      setUploadError("File size must be less than 10MB");
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      // Upload file to backend
      const uploadResult = await uploadFile(file);
      
      const fileData = {
        ...file,
        fileId: uploadResult.fileId,
        uploadSuccess: true
      };
      
      setUploadedFile(fileData);
      onFileSelect(fileData);
      
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadError(`Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleChange = (e) => {
    const file = e.target.files[0];
    handleFileSelect(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const resetUpload = () => {
    setUploadedFile(null);
    setUploadError(null);
    onFileSelect(null);
  };

  return (
    <div className="upload-section">
      {!uploadedFile ? (
        <div
          className={`upload-box ${isDragOver ? "drag-over" : ""} ${isUploading ? "uploading" : ""}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="upload-content">
            {isUploading ? (
              <>
                <div className="upload-spinner">⏳</div>
                <h3>Uploading...</h3>
                <p>Please wait while we process your document</p>
              </>
            ) : (
              <>
                <div className="upload-icon">📄</div>
                <h3>Upload your claim document</h3>
                <p>Drag and drop a PDF file here, or click to browse</p>
                <label className="upload-button">
                  Choose File
                  <input 
                    type="file" 
                    accept="application/pdf" 
                    onChange={handleChange}
                    disabled={isUploading}
                    hidden
                  />
                </label>
                <p className="upload-hint">Supported format: PDF (Max 10MB)</p>
              </>
            )}
            
            {uploadError && (
              <div className="upload-error">
                <span className="error-icon">⚠️</span>
                <span>{uploadError}</span>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="file-uploaded">
          <div className="file-success">
            <div className="success-icon">✓</div>
            <div className="file-details">
              <h4>File uploaded successfully!</h4>
              <p className="file-name">{uploadedFile.name}</p>
              <p className="file-size">
                {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <p className="file-id">File ID: {uploadedFile.fileId}</p>
            </div>
            <button 
              className="change-file-btn"
              onClick={resetUpload}
            >
              Change File
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;