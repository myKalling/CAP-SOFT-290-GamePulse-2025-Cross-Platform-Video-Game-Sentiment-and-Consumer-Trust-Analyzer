import { useEffect, useState } from "react";
import { ActivityIndicator, Platform, StyleSheet, View, TextInput, FlatList, Text, Alert, Pressable } from "react-native";
import { read } from "@/api/fetch-wrapper";

type SearchGame = {
  GameID: number;
  Title: string;
};

type GameDetails = SearchGame & {
  Price: number | null;
};

type GameSummary = {
  ReviewCount: number;
  AverageSentiment: number | null;
  PositiveReviews: number;
  NegativeReviews: number;
  NeutralReviews: number;
};

export default function FilterAndSearch() {
  const [searchText, setSearchText] = useState("");
  const [filteredGames, setFilteredGames] = useState<SearchGame[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameDetails | null>(null);
  const [gameSummary, setGameSummary] = useState<GameSummary | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  // making the search prettier by trimming whitespace and filtering results. 
  const incrementalResults = searchText.trim()
    ? filteredGames.filter((game) =>
        game.Title.toLowerCase().includes(searchText.trim().toLowerCase())
      )
    : [];

  //makes sure the search results are updated as the user types
  const handleSearchTextChange = (text: string) => {
    setSearchText(text);

    if (!text.trim()) {
      setFilteredGames([]);
      setSelectedGame(null);
      setGameSummary(null);
      setDetailsError(null);
    }
  };

  const closeSearchResults = () => {
    setFilteredGames([]);
    setSelectedGame(null);
    setGameSummary(null);
    setDetailsError(null);
  };

  //closes the search results when clicking outside the search container
  useEffect(() => {
    if (Platform.OS !== "web") return;

    const handleOutsidePointerDown = (event: PointerEvent) => {
      const target = event.target;
      const searchContainer = document.getElementById("game-search-container");

      if (
        target instanceof Element &&
        searchContainer &&
        !searchContainer.contains(target)
      ) {
        closeSearchResults();
      }
    };

    document.addEventListener("pointerdown", handleOutsidePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handleOutsidePointerDown);
    };
  }, []);


  useEffect(() => {
    const query = searchText.trim();
    if (!query) return;

    const timeoutId = setTimeout(async () => {
      try {
        // finding games that match the search query
        const data = await read(
          `games/search?search_term=${encodeURIComponent(query)}`
        );
        // returns the api data to an array
        setFilteredGames(Array.isArray(data) ? data as SearchGame[] : []);
        setSelectedGame(null);
        setGameSummary(null);
        setDetailsError(null);
      } catch (error) {
        setDetailsError(
          error instanceof Error ? error.message : "Failed to search games."
        );
        setFilteredGames([]);
      }
    }, 250);

    // cleanup function to clear the timeout if the component unmounts or searchText changes
    return () => clearTimeout(timeoutId);
  }, [searchText]);


  // this handles the search when the user presses the search button
  const handleSearch = async () => {
    const query = searchText.trim();
    if (!query) {
      Alert.alert("Invalid Search", "Please enter a game name.");
      return;
    }

    try {
      const data = await read(
        `games/search?search_term=${encodeURIComponent(query)}`
      );
      const games = Array.isArray(data) ? data as SearchGame[] : [];
      setFilteredGames(games);
      setSelectedGame(null);
      setGameSummary(null);
      setDetailsError(null);

      if (games.length === 0) {
        Alert.alert("No Results", `No game found matching "${searchText}".`);
      }
    } catch (error) {
      Alert.alert(
        "Error",
        error instanceof Error ? error.message : "Failed to fetch games from database."
      );
    }
  };


  // this opens the game details when a game is selected from the search results
  const openGameDetails = async (game: SearchGame) => {
    setDetailsLoading(true);
    setDetailsError(null);
    setSelectedGame(null);
    setGameSummary(null);

    try {

      // Promise.all to fetch both game details and summary concurrently
      const [details, summary] = await Promise.all([
        read(`queries/games/${game.GameID}`),
        read(`games/${game.GameID}/summary`),
      ]);
      setSelectedGame(details as GameDetails);
      setGameSummary(summary as GameSummary);
    } catch (error) {
      setDetailsError(
        error instanceof Error ? error.message : "Failed to load game details."
      );
    } finally {
      setDetailsLoading(false);
    }
  };

  return (
    <View
      nativeID="game-search-container"
      style={styles.container}
    >
      <TextInput
        style={styles.input}
        placeholder="Search for a game..."
        value={searchText}
        onChangeText={handleSearchTextChange}
        onBlur={closeSearchResults}
      />
      <Pressable style={styles.searchButton} onPress={handleSearch}>
        <Text style={styles.searchButtonText}>Search</Text>
      </Pressable>

      {incrementalResults.length > 0 && (
        <FlatList
          style={styles.results}
          data={incrementalResults}
          keyExtractor={(item) => String(item.GameID)}
          renderItem={({ item }) => (
            <Pressable
              style={styles.gameItem}
              onPress={() => openGameDetails(item)}
              accessibilityRole="button"
            >
              <Text>{item.Title}</Text>
            </Pressable>
          )}
        />
      )}

      {(detailsLoading || detailsError || selectedGame) && (
        <View style={styles.details}>
          {detailsLoading && <ActivityIndicator color="#ba191b" />}
          {detailsError && (
            <Text style={styles.detailsError}>{detailsError}</Text>
          )}
          {selectedGame && (
            <>
              <View style={styles.detailsHeader}>
                <Text style={styles.detailsTitle}>{selectedGame.Title}</Text>
                <Pressable
                  onPress={() => {
                    setSelectedGame(null);
                    setGameSummary(null);
                  }}
                  accessibilityRole="button"
                >
                  <Text style={styles.closeText}>Close</Text>
                </Pressable>
              </View>
              <Text style={styles.detailText}>
                Price: {selectedGame.Price == null
                  ? "N/A"
                  : selectedGame.Price === 0
                    ? "Free"
                    : `$${selectedGame.Price.toFixed(2)}`}
              </Text>
              {gameSummary && (
                <>
                  <Text style={styles.detailText}>
                    Reviews: {gameSummary.ReviewCount}
                  </Text>
                  {gameSummary.AverageSentiment != null && (
                    <Text style={styles.detailText}>
                      Average Sentiment: {gameSummary.AverageSentiment.toFixed(2)}
                    </Text>
                  )}
                  <Text style={styles.detailText}>
                    Positive: {gameSummary.PositiveReviews} ·
                    Neutral: {gameSummary.NeutralReviews} ·
                    Negative: {gameSummary.NegativeReviews}
                  </Text>
                </>
              )}
            </>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    position: "relative",
    
    borderRadius: 6,
    backgroundColor: "#fff",
  },
  input: {
    width: 180,
    borderWidth: 1,
    borderColor: "#ccc",
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderTopRightRadius: 0,
    borderBottomRightRadius: 0,
    marginRight: 0,
  },
  searchButton: {
    marginLeft: 0,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderTopLeftRadius: 0,
    borderBottomLeftRadius: 0,
    backgroundColor: "#ba191b",
  },
  searchButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  results: {
    position: "absolute",
    top: 44,
    right: 12,
    width: 260,
    maxHeight: 240,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 6,
  },
  gameItem: {
    padding: 10,
    fontSize: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#eee",
  },
  details: {
    position: "absolute",
    top: 44,
    right: 280,
    width: 300,
    maxHeight: 280,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 6,
    padding: 12,
  },
  detailsHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  detailsTitle: {
    flex: 1,
    color: "#111",
    fontSize: 16,
    fontWeight: "700",
  },
  closeText: {
    color: "#ba191b",
    fontWeight: "700",
  },
  detailText: {
    color: "#333",
    marginBottom: 4,
  },
  detailsError: {
    color: "#ba191b",
  },
});