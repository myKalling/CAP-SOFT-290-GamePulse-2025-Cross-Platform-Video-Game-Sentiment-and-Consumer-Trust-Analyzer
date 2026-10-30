import React from "react";

interface EmailLinkProps {
  recipient: string;
  subject?: string;
  body?: string;
}

const EmailLink: React.FC<EmailLinkProps> = ({ recipient, subject = "Enter Subject", body = "This is a pre-filled email body." }) => {

  // Encode subject and body for safe URL usage
  const mailtoLink = `mailto:${recipient}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <a
      href={mailtoLink}
      style={{
        color: "#0078D4",
        textDecoration: "underline",
        fontWeight: "bold",
      }}
    >
      Send Email
    </a>
  );
};

export default EmailLink;