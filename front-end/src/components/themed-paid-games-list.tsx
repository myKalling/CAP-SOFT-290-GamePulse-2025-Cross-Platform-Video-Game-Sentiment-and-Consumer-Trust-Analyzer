import { useState } from 'react';
import { useColorScheme } from 'react-native';
import { FlatList, Pressable, Text, View } from 'react-native';
const PAYITEMS = [
  { id: 1, name: ' R.E.P.O' },
  { id: 2, name: 'Hollow Knight: Silksong' },
  { id: 3, name: 'ARC Raiders' },
  { id: 4, name: 'PEAK' },
  { id: 5, name: 'BattleField tm 6' },
  { id: 6, name: 'Monster Hunter Wilds' },
  { id: 7, name: 'Schedule 1' },
  { id: 8, name: 'Clair Obscur: Expedition 33' },
  { id: 9, name: 'Kingdom Come: Deliverance 2' },
  { id: 10, name: 'ELDEN RING NIGHTREIGN' },
];

export default function PaidGamesList() {
  const [selected, setSelected] = useState<string | null>(null);
  const colorScheme = useColorScheme();
  const ink = { color: colorScheme === 'dark' ? '#FFFFFF' : '#000000' };

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <FlatList
        data={PAYITEMS}
        keyExtractor={item => String(item.id)}
        renderItem={({ item }) => (
          <Pressable onPress={() => setSelected(item.name)}>
            <Text style={ink}>{item.name}</Text>
          </Pressable>
        )}
      />
      {selected != null && <Text style={ink}>{`Selected: ${selected}`}</Text>}
    </View>
  );
}