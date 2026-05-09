import React from 'react';
import { RecruiterPromptBar } from './components/RecruiterPromptBar';
import { ResumePreview } from './components/ResumePreview';
export function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <RecruiterPromptBar />
      <ResumePreview />
    </div>);

}