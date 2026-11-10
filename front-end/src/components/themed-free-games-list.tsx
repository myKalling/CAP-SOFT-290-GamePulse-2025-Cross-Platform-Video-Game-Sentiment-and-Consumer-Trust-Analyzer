import { useState } from 'react';
import { useColorScheme } from 'react-native';
import { FlatList, Pressable, Text, View } from 'react-native';


const FREEITEMS = [
  { id: 1, name: ' Where Winds Meet' },
  { id: 2, name: 'skate.' },
  { id: 3, name: 'Arena Breakout: Infinitee' },
  { id: 4, name: 'FragPunk' },
  { id: 5, name: 'ENA: Dream BBQ' },
  { id: 6, name: 'Mecha BREAK' },
  { id: 7, name: 'Blue Protocol: Star Resonance' },
  { id: 8, name: 'Battlefield tm REDSEC' },
  { id: 9, name: 'DRAGON BALL GEKISHIN SUADRA' },
  { id: 10, name: 'The Mr. Rabbit Magic Show' },
];

export default function FreeGamesList() {
  const [selected, setSelected] = useState<string | null>(null);
  const colorScheme = useColorScheme();
  const ink = { color: colorScheme === 'dark' ? '#FFFFFF' : '#000000' };

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <FlatList
        data={FREEITEMS}
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