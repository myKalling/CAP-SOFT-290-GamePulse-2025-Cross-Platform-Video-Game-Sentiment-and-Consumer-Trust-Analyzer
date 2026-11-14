import { openBrowserAsync } from "expo-web-browser";
import React from "react";
import { Platform, Pressable, StyleSheet } from "react-native";

import { ThemedText } from "@/components/themed-text";

interface EmailLinkProps {
  recipient: string;
  subject?: string;
  body?: string;
}

const EmailLink: React.FC<EmailLinkProps> = ({ recipient, subject = "Enter Subject", body = "This is a pre-filled email body." }) => {

  // Encode subject and body for safe URL usage
  const mailtoLink = `mailto:${recipient}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  const handlePress = async () => {
    if (Platform.OS === "web") {
      window.location.href = mailtoLink;
    } else {
      await openBrowserAsync(mailtoLink);
    }
  };

  return (
    <Pressable onPress={handlePress}>
      <ThemedText style={styles.link}>Send Email</ThemedText>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  link: {
    textAlign: 'center',
    color: "#0078D4",
    textDecorationLine: "underline",
    fontWeight: "bold",
  },
});

export default EmailLink;