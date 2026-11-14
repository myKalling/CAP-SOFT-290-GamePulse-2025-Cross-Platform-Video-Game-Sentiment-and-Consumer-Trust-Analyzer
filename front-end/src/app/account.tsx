import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { useAuth } from "../../authorization/authorization-login";
import { ThemedView } from "@/components/themed-view";
import { ThemedText } from "@/components/themed-text";
import { Spacing } from "@/constants/theme";


export default function AccountScreen() {
  const { username, signIn, signOut } = useAuth();
  const [accountName, setAccountName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");

  const signUp = (): void => {
    const name = accountName.trim();
    if (!name) {
      setError("Please enter an account name.");
      return;
    }
    setError("");
    signIn(name);
  };

  const login = (): void => {
    signUp();
  };

  if (username) {
    return (
      <ThemedView style={styles.container}>
        <Text style={styles.title}>
          Signed in as {username}
        </Text>

        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={styles.signUpButton}
            onPress={signOut}
          >
            <Text style={styles.buttonText}>
              Sign Out
            </Text>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title" style={[styles.title, { color: '#ba191b' }]}>
        Sign Up /
      </ThemedText>
      <ThemedText type="title" style={[styles.title, { color: '#161a1d' }]}>
         Log In
      </ThemedText>

      <View style={styles.form}>
        <Text style={styles.label}>
          Account Name
        </Text>

        <TextInput
          style={styles.input}
          value={accountName}
          onChangeText={setAccountName}
          placeholder="Enter account name here"
        />

        
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={styles.signUpButton}
            onPress={signUp}
          >
            <Text style={styles.buttonText}>
              Sign Up
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.signUpButton}
            onPress={login}
          >
            <Text style={styles.buttonText}>
              Log In
            </Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.errorText}>
          {error}
        </Text>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
  },

  title: {
    fontSize: 32,
    fontWeight: "bold",
    marginBottom: 20,
    textAlign: "center",
  },

  form: {
    padding: 20,
    borderWidth: 2,
    
  },

  label: {
    fontWeight: "bold",
    marginBottom: 6,
    marginTop: 12,
    textAlign: "center",
  },

  input: {
    borderWidth: 1,
    padding: 12,
    textAlign: "center",
    
  },

  buttonContainer: {
    flexDirection: "row",
    marginTop: 20,
    justifyContent: "center",
  },

  signUpButton: {
    padding: 12,
    marginRight: 10,
    textAlign: "center",
  },

  buttonText: {
    fontWeight: "bold",
    textAlign: "center",
  },

  errorText: {
    marginTop: 10,
  },
});

