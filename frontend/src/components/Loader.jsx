import React from "react";

const Loader = () => {
  return (
    <div className="loader-container">
      <div className="loader">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span className="loader-text">Analyzing...</span>
    </div>
  );
};

export default Loader;