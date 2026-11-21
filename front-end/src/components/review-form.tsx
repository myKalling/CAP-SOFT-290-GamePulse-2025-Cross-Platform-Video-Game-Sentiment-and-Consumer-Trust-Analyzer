import { useState, type FormEvent } from "react";
import "./ReviewForm.css";

type Status = "idle" | "submitting" | "success" | "error";

interface ReviewPayload {
  gameId: string;
  review: string;
  rating: number;
  accountName: string;
  date: string;
  platform: string;
  genre: string;
  reviewId: string;
  visibility: "public" | "private";
}

const ReviewForm = () => {
  const [status, setStatus] = useState<Status>("idle");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setStatus("submitting");
    // Handle form submission logic here
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields go here */}
      <button type="submit">Submit Review</button>
    </form>
  );
};

export default ReviewForm;

async function submitReview(payload: ReviewPayload): Promise<void> {
  try {
    const response = await fetch("/api/reviews", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("Failed to submit review");
    }
  } catch (error) {
    console.error(error);
    throw error;
  }
}

export default submitReview;