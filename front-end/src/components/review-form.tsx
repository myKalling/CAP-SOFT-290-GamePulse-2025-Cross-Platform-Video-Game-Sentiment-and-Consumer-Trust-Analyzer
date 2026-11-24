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
  return (
    <div>
      <p>Review submission is not available yet.</p>
      <button type="button" disabled>Submit Review</button>
    </div>
  );
};

export default ReviewForm;

export async function submitReview(payload: ReviewPayload): Promise<void> {
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