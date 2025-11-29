import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Image,
  Modal,
  ActivityIndicator,
  AlertButton,
  ScrollView,
  Platform
} from 'react-native';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../../utils/api';
import * as ImagePicker from 'expo-image-picker';
import { OrderStatus, DeliveryPersonStatus } from '../../types';

interface Order {
  id: string;
  customer_name: string;
  customer_phone: number;
  delivery_address: string;
  items: string[];
  status: OrderStatus;
  created_at: number;
  latitude: number;
  longitude: number;
  proof_image?: string;
}

export default function Home() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [filter, setFilter] = useState('all');
  const { user } = useAuth();

  const fetchOrders = async () => {
    try {
      const response = await api.get('/orders/current');
      setOrders(response.data);
    } catch (error: any) {
      console.error('Error fetching orders:', error);
      Alert.alert('Error', 'Failed to load orders');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchOrders();
  };

  const updateOrderStatus = async (orderId: string, newStatus: OrderStatus) => {
    try {
      await api.patch(`/orders/${orderId}/status?status=${newStatus}`);
      Alert.alert('Success', 'Order status updated successfully');
      fetchOrders();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update order status');
    }
  };

  const pickImage = async (orderId: string) => {
    try {
      // Use launchImageLibraryAsync which works better on web and allows camera access on mobile
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.5,
      });

      if (!result.canceled) {
        completeDelivery(orderId, result.assets[0].uri);
      }
    } catch (error) {
      console.error('ImagePicker Error:', error);
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  const completeDelivery = async (orderId: string, imageUri: string) => {
    setUploading(true);
    try {
      const formData = new FormData();

      if (Platform.OS === 'web') {
        const response = await fetch(imageUri);
        const blob = await response.blob();
        formData.append('file', blob, 'proof.jpg');
      } else {
        formData.append('file', {
          uri: imageUri,
          name: 'proof.jpg',
          type: 'image/jpeg',
        } as any);
      }

      await api.post(`/orders/${orderId}/complete`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      Alert.alert('Success', 'Order delivered successfully!');
      fetchOrders();
    } catch (error: any) {
      console.error('Error completing delivery:', error);
      Alert.alert('Error', error.response?.data?.detail || 'Failed to complete delivery');
    } finally {
      setUploading(false);
    }
  };

  const handleStatusChange = (order: Order) => {
    setSelectedOrder(order);
    setModalVisible(true);
  };

  const getStatusColor = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.PENDING:
        return '#F59E0B';
      case OrderStatus.IN_TRANSIT:
        return '#3B82F6';
      case OrderStatus.REACHED:
        return '#8B5CF6';
      case OrderStatus.DELIVERED:
        return '#10B981';
      default:
        return '#6B7280';
    }
  };

  const getStatusIcon = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.PENDING:
        return 'time';
      case OrderStatus.IN_TRANSIT:
        return 'bicycle';
      case OrderStatus.REACHED:
        return 'location';
      default:
        return 'checkmark-circle';
    }
  };

  const getStatusLabel = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.PENDING:
        return 'New Order';
      case OrderStatus.IN_TRANSIT:
        return 'In Transit';
      case OrderStatus.REACHED:
        return 'Reached Location';
      case OrderStatus.DELIVERED:
        return 'Delivered';
      default:
        return status;
    }
  }

  const renderOrder = ({ item }: { item: Order }) => (
    <TouchableOpacity
      style={styles.orderCard}
      onPress={() => handleStatusChange(item)}
      activeOpacity={0.7}
    >
      <View style={styles.orderHeader}>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Ionicons
            name={getStatusIcon(item.status) as any}
            size={16}
            color="#fff"
          />
          <Text style={styles.statusText}>
            {getStatusLabel(item.status)}
          </Text>
        </View>
        <View style={styles.dateContainer}>
          <Ionicons name="calendar-outline" size={14} color="#9CA3AF" />
          <Text style={styles.orderDate}>
            {new Date(item.created_at * 1000).toLocaleDateString()}
          </Text>
        </View>
      </View>

      <View style={styles.customerInfo}>
        <Text style={styles.customerName}>{item.customer_name}</Text>
        <View style={styles.detailRow}>
          <Ionicons name="call" size={16} color="#6366F1" />
          <Text style={styles.detailText}>{item.customer_phone}</Text>
        </View>
      </View>

      <View style={styles.separator} />

      <View style={styles.orderDetails}>
        <View style={styles.detailRow}>
          <Ionicons name="location" size={18} color="#EF4444" />
          <Text style={styles.addressText}>{item.delivery_address}</Text>
        </View>

        <View style={styles.itemsContainer}>
          <Ionicons name="bag-handle" size={18} color="#10B981" />
          <View style={{ flex: 1 }}>
            {item.items.map((orderItem, index) => (
              <Text key={index} style={styles.itemsText}>• {orderItem}</Text>
            ))}
          </View>
        </View>
      </View>

      <View style={styles.actionHint}>
        <Text style={styles.actionHintText}>
          {item.status === OrderStatus.REACHED ? 'Tap to complete delivery' : 'Tap to update status'}
        </Text>
        <Ionicons name="chevron-forward" size={16} color="#9CA3AF" />
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.loadingText}>Loading orders...</Text>
      </View>
    );
  }

  const filteredOrders = orders.filter(order => {
    if (filter === 'all') return true;
    return order.status === filter;
  });

  if (user?.status === DeliveryPersonStatus.INACTIVE) {
    return (
      <View style={[styles.container, styles.centerContainer, { padding: 20 }]}>
        <Ionicons name="warning" size={64} color="#F59E0B" style={{ marginBottom: 20 }} />
        <Text style={[styles.welcomeText, { textAlign: 'center' }]}>Account Inactive</Text>
        <Text style={[styles.emptySubtext, { textAlign: 'center', marginTop: 10 }]}>
          You are currently inactive. You cannot view or accept orders.
        </Text>
        <Text style={[styles.emptySubtext, { textAlign: 'center', marginBottom: 30 }]}>
          Please go to your Profile to activate your status.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.welcomeHeader}>
        <Text style={styles.welcomeText}>Welcome, {user?.name}!</Text>
        <Text style={styles.ordersCount}>{orders.length} active orders</Text>
      </View>

      <View style={styles.filterContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterContent}>
          {['all', ...Object.values(OrderStatus)].map((status) => (
            <TouchableOpacity
              key={status}
              style={[
                styles.filterChip,
                filter === status && styles.activeFilterChip
              ]}
              onPress={() => setFilter(status)}
            >
              <Text style={[
                styles.filterText,
                filter === status && styles.activeFilterText
              ]}>
                {status === 'all' ? 'All' : getStatusLabel(status as OrderStatus)}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {filteredOrders.length === 0 ? (
        <View style={styles.emptyContainer}>
          <View style={styles.emptyIconContainer}>
            <Ionicons name="bicycle-outline" size={80} color="#D1D5DB" />
          </View>
          <Text style={styles.emptyText}>No Orders Found</Text>
          <Text style={styles.emptySubtext}>Try changing the filter</Text>
          <Text style={styles.refreshHint}>Pull down to refresh</Text>
        </View>
      ) : (
        <FlatList
          data={filteredOrders}
          renderItem={renderOrder}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContainer}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#6366F1"
            />
          }
        />
      )}

      {uploading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#ffffff" />
          <Text style={styles.uploadingText}>Uploading proof...</Text>
        </View>
      )}

      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.centeredView}>
          <View style={styles.modalView}>
            <Text style={styles.modalTitle}>Update Order Status</Text>

            {selectedOrder?.status === OrderStatus.PENDING && (
              <TouchableOpacity
                style={[styles.button, styles.buttonPrimary]}
                onPress={() => {
                  setModalVisible(false);
                  updateOrderStatus(selectedOrder.id, OrderStatus.IN_TRANSIT);
                }}
              >
                <Text style={styles.textStyle}>Start Delivery</Text>
              </TouchableOpacity>
            )}

            {selectedOrder?.status === OrderStatus.REACHED && (
              <TouchableOpacity
                style={[styles.button, styles.buttonSuccess]}
                onPress={() => {
                  setModalVisible(false);
                  pickImage(selectedOrder.id);
                }}
              >
                <Text style={styles.textStyle}>Complete Delivery</Text>
              </TouchableOpacity>
            )}

            <TouchableOpacity
              style={[styles.button, styles.buttonClose]}
              onPress={() => setModalVisible(false)}
            >
              <Text style={[styles.textStyle, { color: '#374151' }]}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  welcomeHeader: {
    backgroundColor: '#fff',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  ordersCount: {
    fontSize: 14,
    color: '#6B7280',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: '#6B7280',
  },
  listContainer: {
    padding: 16,
  },
  orderCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  statusText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
  dateContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  orderDate: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  customerInfo: {
    marginBottom: 12,
  },
  customerName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 6,
  },
  separator: {
    height: 1,
    backgroundColor: '#E5E7EB',
    marginVertical: 12,
  },
  orderDetails: {
    gap: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  detailText: {
    fontSize: 14,
    color: '#6B7280',
    flex: 1,
  },
  addressText: {
    fontSize: 14,
    color: '#374151',
    flex: 1,
    lineHeight: 20,
  },
  itemsContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: '#F0FDF4',
    padding: 12,
    borderRadius: 8,
    marginTop: 4,
  },
  itemsText: {
    fontSize: 14,
    color: '#059669',
    fontWeight: '500',
    marginBottom: 2,
  },
  actionHint: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    gap: 4,
  },
  actionHintText: {
    fontSize: 13,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyIconContainer: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  emptyText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#374151',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 15,
    color: '#6B7280',
    marginBottom: 24,
  },
  refreshHint: {
    fontSize: 13,
    color: '#9CA3AF',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  uploadingText: {
    fontWeight: '600',
  },
  centeredView: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalView: {
    margin: 20,
    backgroundColor: 'white',
    borderRadius: 20,
    padding: 35,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
    width: '80%',
  },
  button: {
    borderRadius: 10,
    padding: 15,
    elevation: 2,
    width: '100%',
    marginBottom: 10,
    alignItems: 'center',
  },
  buttonPrimary: {
    backgroundColor: '#3B82F6',
  },
  buttonSuccess: {
    backgroundColor: '#10B981',
  },
  buttonClose: {
    backgroundColor: '#F3F4F6',
  },
  textStyle: {
    color: 'white',
    fontWeight: 'bold',
    textAlign: 'center',
    fontSize: 16,
  },
  modalTitle: {
    marginBottom: 20,
    textAlign: 'center',
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
  },
  filterContainer: {
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  filterContent: {
    paddingHorizontal: 16,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#F3F4F6',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  activeFilterChip: {
    backgroundColor: '#6366F1',
    borderColor: '#6366F1',
  },
  filterText: {
    fontSize: 14,
    color: '#4B5563',
    fontWeight: '500',
  },
  activeFilterText: {
    color: '#fff',
  },
});
