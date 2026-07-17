import { useCallback, useEffect, useState } from "react";
import { listAppointments, type Appointment } from "../api/appointments";
import { usePetDirectory } from "./usePetDirectory";

export interface DirectoryAppointment extends Appointment {
  petName: string;
  ownerName: string;
  ownerId: string;
}

export function useAppointmentDirectory(token: string) {
  const petDirectory = usePetDirectory(token);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    listAppointments(token)
      .then((data) => {
        setAppointments(data);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load appointments"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const petsById = new Map(petDirectory.pets.map((pet) => [pet.id, pet]));
  const decorated: DirectoryAppointment[] = appointments.map((appointment) => {
    const pet = petsById.get(appointment.pet_id);
    return {
      ...appointment,
      petName: pet?.name ?? "Unknown pet",
      ownerName: pet?.ownerName ?? "Unknown owner",
      ownerId: pet?.ownerId ?? "",
    };
  });

  return {
    appointments: decorated,
    loading: loading || petDirectory.loading,
    error: error ?? petDirectory.error,
    refresh,
  };
}
