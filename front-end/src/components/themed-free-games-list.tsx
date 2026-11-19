import { useState } from 'react';
import Animated, { FadeInUp, FadeOutDown, ReduceMotion } from 'react-native-reanimated';
import { Platform, useColorScheme, StyleSheet, useWindowDimensions } from 'react-native';
import { FlatList, Pressable, Text, View } from 'react-native';
import { Colors } from '@/constants/theme';


import ReviewInput from '@/constants/theme-user-review-input';

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
  const [isOpen, setIsOpen] = useState(false);
  const [isClosed, setIsClosed] = useState(false);
  const colorScheme = useColorScheme();
  const ink = {color: colorScheme === 'dark' ? '#FFFFFF' : '#000000',};
  const { width } = useWindowDimensions();
  const fontSize = width < 768 ? 14 : 24;

  return (
      <View style={[styles.container, { flexDirection: Platform.OS === 'ios' ? 'row' : 'column' }]}>
        <Pressable
          style={styles.button}
          onPress={() => setIsOpen((prev) => !prev)}
        >
          
            <Text style={[styles.buttonText, { fontSize }]}>
              Free to Play 
            </Text>
          
        </Pressable>
  
        {isOpen && (
          <Animated.View
            entering={FadeInUp.duration(220).reduceMotion(ReduceMotion.Never)}
            style={styles.dropdown}>
            {FREEITEMS.map((item) => (
              <Pressable
                key={item.id}
                style={styles.item}
                onPress={() => {
                  setSelected(item.name);
                  setIsOpen(false);
                }}
              >
                <Text style={styles.itemText}>
                  {item.name}
                </Text>
              </Pressable>
            ))}
          </Animated.View>
         )}
      
        {!isOpen && selected && (
          <>
            <Text style={[styles.selectedText, ink]}>
              {selected}
            </Text>
            <ReviewInput gameName={selected} />
          </>
        )}
        
      </View>
    );
  }
  
  const styles = StyleSheet.create({
    container: {
      flex: 1,
      padding: 20,
      
    },
  
    button: {
      backgroundColor: Colors.tabs.background,
      padding: 10,
      borderRadius: 8,
    },
  
    buttonText: {
      color: Colors.tabs.text,
      fontWeight: '600',
      textAlign: 'center',
    },
  
    dropdown: {
      marginTop: 5,
      borderRadius: 8,
      backgroundColor:'#d8d8da'
    },
  
    item: {
      padding: 12,
      borderBottomWidth: 1,
      borderBottomColor:'#e6e6e9',
    },
  
    itemText: {
      fontSize: 16,
      color: Colors.tabs.text,
    },
  
    selectedText: {
      marginTop: 20,
      fontSize: 18,
      fontWeight: '600',
    },
  });
  