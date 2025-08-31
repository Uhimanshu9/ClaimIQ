import React, { useState } from "react";
import FileUpload from "../components/FileUpload";
import ChatBox from "../components/ChatBox";

const Home = () => {
  const [file, setFile] = useState(null);

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">Claim IQ</h1>
          <p className="app-subtitle">Intelligent Claims Analysis Assistant</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <FileUpload onFileSelect={setFile} />
        {file && <ChatBox file={file} />}
      </main>
    </div>
  );
};

export default Home;