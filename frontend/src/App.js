import React, { useState, useEffect } from 'react';
import './App.css';
import { Calendar } from './components/ui/calendar';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Textarea } from './components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Badge } from './components/ui/badge';
import { CalendarDays, MapPin, Users, Clock, Star, Wifi, Car, Coffee, Tv } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [selectedDates, setSelectedDates] = useState({ from: null, to: null });
  const [bookingData, setBookingData] = useState({
    name: '',
    email: '',
    phone: '',
    guests: '',
    arrivalTime: '',
    specialRequests: ''
  });
  const [pricing, setPricing] = useState({ base_rate: 120, baseRate: 120 });
  const [isBookingOpen, setIsBookingOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [bookings, setBookings] = useState([]);

  const apartmentImages = [
    'https://images.unsplash.com/photo-1638454668466-e8dbd5462f20',
    'https://images.unsplash.com/photo-1583847268964-b28dc8f51f92',
    'https://images.unsplash.com/photo-1556020685-ae41abfc9365',
    'https://images.unsplash.com/photo-1484154218962-a197022b5858'
  ];

  const amenities = [
    { icon: Wifi, name: 'WiFi gratuit' },
    { icon: Car, name: 'Parking' },
    { icon: Coffee, name: 'Cuisine équipée' },
    { icon: Tv, name: 'TV écran plat' }
  ];

  const arrivalTimeSlots = [
    '14:00 - 16:00',
    '16:00 - 18:00', 
    '18:00 - 20:00',
    '20:00 - 22:00'
  ];

  useEffect(() => {
    fetchBookings();
    fetchPricing();
  }, []);

  const fetchBookings = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/bookings`);
      if (response.ok) {
        const data = await response.json();
        setBookings(data);
      }
    } catch (error) {
      console.error('Error fetching bookings:', error);
    }
  };

  const fetchPricing = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/pricing`);
      if (response.ok) {
        const data = await response.json();
        setPricing(data);
      }
    } catch (error) {
      console.error('Error fetching pricing:', error);
    }
  };

  const isDateBooked = (date) => {
    return bookings.some(booking => {
      const checkIn = new Date(booking.check_in);
      const checkOut = new Date(booking.check_out);
      return date >= checkIn && date <= checkOut;
    });
  };

  const calculateNights = () => {
    if (selectedDates.from && selectedDates.to) {
      const timeDiff = selectedDates.to.getTime() - selectedDates.from.getTime();
      return Math.ceil(timeDiff / (1000 * 3600 * 24));
    }
    return 0;
  };

  const calculateTotal = () => {
    const nights = calculateNights();
    const baseRate = pricing.base_rate || pricing.baseRate || 120;
    return nights * baseRate;
  };

  const handleBookingSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const bookingPayload = {
        ...bookingData,
        check_in: selectedDates.from?.toISOString().split('T')[0],
        check_out: selectedDates.to?.toISOString().split('T')[0],
        nights: calculateNights(),
        total_price: calculateTotal(),
        guests: parseInt(bookingData.guests)
      };

      const response = await fetch(`${BACKEND_URL}/api/bookings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(bookingPayload),
      });

      if (response.ok) {
        alert('Réservation confirmée ! Vous recevrez un email de confirmation.');
        setIsBookingOpen(false);
        setSelectedDates({ from: null, to: null });
        setBookingData({
          name: '',
          email: '',
          phone: '',
          guests: '',
          arrivalTime: '',
          specialRequests: ''
        });
        fetchBookings();
      } else {
        const error = await response.json();
        alert('Erreur lors de la réservation: ' + error.detail);
      }
    } catch (error) {
      console.error('Error submitting booking:', error);
      alert('Erreur de connexion. Veuillez réessayer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-slate-900">Appartement de Luxe</h1>
            <Badge variant="secondary" className="px-3 py-1">
              <Star className="w-4 h-4 mr-1 fill-yellow-400 text-yellow-400" />
              4.9
            </Badge>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <h2 className="text-5xl font-bold text-slate-900 leading-tight">
                  Votre séjour parfait vous attend
                </h2>
                <p className="text-xl text-slate-600 leading-relaxed">
                  Découvrez notre appartement moderne et élégant, parfaitement équipé pour un séjour inoubliable.
                </p>
              </div>
              
              <div className="flex items-center space-x-6 text-slate-600">
                <div className="flex items-center space-x-2">
                  <MapPin className="w-5 h-5" />
                  <span>Centre-ville</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Users className="w-5 h-5" />
                  <span>Jusqu'à 4 personnes</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CalendarDays className="w-5 h-5" />
                  <span>Séjours flexibles</span>
                </div>
              </div>

              <div className="bg-white/70 backdrop-blur-sm p-6 rounded-2xl shadow-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-3xl font-bold text-slate-900">€{pricing.base_rate || pricing.baseRate || 120}</span>
                    <span className="text-slate-600 ml-2">par nuit</span>
                  </div>
                  <Dialog open={isBookingOpen} onOpenChange={setIsBookingOpen}>
                    <DialogTrigger asChild>
                      <Button size="lg" className="bg-slate-900 hover:bg-slate-800 text-white px-8">
                        Réserver maintenant
                      </Button>
                    </DialogTrigger>
                  </Dialog>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {apartmentImages.map((image, index) => (
                <div key={index} className={`rounded-2xl overflow-hidden shadow-lg ${index === 0 ? 'col-span-2 aspect-[2/1]' : 'aspect-square'}`}>
                  <img 
                    src={image} 
                    alt={`Appartement ${index + 1}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Booking Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-slate-900 mb-4">Choisissez vos dates</h3>
            <p className="text-slate-600">Sélectionnez votre période de séjour</p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12">
            <Card className="p-6">
              <CardHeader>
                <CardTitle>Calendrier des disponibilités</CardTitle>
              </CardHeader>
              <CardContent>
                <Calendar
                  mode="range"
                  selected={selectedDates}
                  onSelect={setSelectedDates}
                  disabled={(date) => date < new Date() || isDateBooked(date)}
                  className="rounded-md border w-full"
                />
              </CardContent>
            </Card>

            <Card className="p-6">
              <CardHeader>
                <CardTitle>Résumé de réservation</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {selectedDates.from && selectedDates.to ? (
                  <>
                    <div className="space-y-2 p-4 bg-slate-50 rounded-lg">
                      <div className="flex justify-between">
                        <span>Arrivée:</span>
                        <span className="font-medium">{selectedDates.from.toLocaleDateString('fr-FR')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Départ:</span>
                        <span className="font-medium">{selectedDates.to.toLocaleDateString('fr-FR')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Nombre de nuits:</span>
                        <span className="font-medium">{calculateNights()}</span>
                      </div>
                      <div className="border-t pt-2 flex justify-between text-lg font-bold">
                        <span>Total:</span>
                        <span>€{calculateTotal()}</span>
                      </div>
                    </div>
                    <Button 
                      onClick={() => setIsBookingOpen(true)} 
                      className="w-full bg-slate-900 hover:bg-slate-800"
                      size="lg"
                    >
                      Procéder à la réservation
                    </Button>
                  </>
                ) : (
                  <p className="text-slate-600 text-center py-8">
                    Sélectionnez vos dates pour voir le tarif
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-slate-900 mb-4">Équipements inclus</h3>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {amenities.map((amenity, index) => (
              <Card key={index} className="p-6 text-center hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <amenity.icon className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <h4 className="font-semibold text-slate-900">{amenity.name}</h4>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Booking Dialog */}
      <Dialog open={isBookingOpen} onOpenChange={setIsBookingOpen}>
        <DialogContent className="max-w-md mx-auto">
          <DialogHeader>
            <DialogTitle>Finaliser votre réservation</DialogTitle>
            <DialogDescription>
              Veuillez remplir vos informations pour confirmer la réservation
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleBookingSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nom complet *</Label>
              <Input
                id="name"
                value={bookingData.name}
                onChange={(e) => setBookingData(prev => ({ ...prev, name: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                value={bookingData.email}
                onChange={(e) => setBookingData(prev => ({ ...prev, email: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Téléphone *</Label>
              <Input
                id="phone"
                value={bookingData.phone}
                onChange={(e) => setBookingData(prev => ({ ...prev, phone: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="guests">Nombre de personnes *</Label>
              <Select value={bookingData.guests} onValueChange={(value) => setBookingData(prev => ({ ...prev, guests: value }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionnez" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 personne</SelectItem>
                  <SelectItem value="2">2 personnes</SelectItem>
                  <SelectItem value="3">3 personnes</SelectItem>
                  <SelectItem value="4">4 personnes</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="arrivalTime">Heure d'arrivée *</Label>
              <Select value={bookingData.arrivalTime} onValueChange={(value) => setBookingData(prev => ({ ...prev, arrivalTime: value }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un créneau" />
                </SelectTrigger>
                <SelectContent>
                  {arrivalTimeSlots.map((slot) => (
                    <SelectItem key={slot} value={slot}>{slot}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="requests">Demandes spéciales</Label>
              <Textarea
                id="requests"
                placeholder="Allergies, préférences, etc."
                value={bookingData.specialRequests}
                onChange={(e) => setBookingData(prev => ({ ...prev, specialRequests: e.target.value }))}
              />
            </div>

            {selectedDates.from && selectedDates.to && (
              <div className="bg-slate-50 p-4 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span>Dates:</span>
                  <span>{selectedDates.from.toLocaleDateString('fr-FR')} - {selectedDates.to.toLocaleDateString('fr-FR')}</span>
                </div>
                <div className="flex justify-between">
                  <span>Nuits:</span>
                  <span>{calculateNights()}</span>
                </div>
                <div className="flex justify-between font-bold text-lg">
                  <span>Total:</span>
                  <span>€{calculateTotal()}</span>
                </div>
              </div>
            )}

            <Button 
              type="submit" 
              className="w-full bg-slate-900 hover:bg-slate-800" 
              size="lg"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Traitement...' : 'Confirmer la réservation'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h3 className="text-2xl font-bold mb-4">Appartement de Luxe</h3>
            <p className="text-slate-300 mb-4">Votre séjour parfait vous attend</p>
            <div className="flex items-center justify-center space-x-2">
              <Clock className="w-4 h-4" />
              <span className="text-sm">Check-in: 14h00 - Check-out: 11h00</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;