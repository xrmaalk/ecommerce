export interface Customer {
  id: number
  email: string
  first_name: string
  last_name: string
  date_joined: string
}

export interface SignInPayload {
  email: string
  password: string
}

export interface RegistrationPayload extends SignInPayload {
  first_name: string
  last_name: string
  password_confirm: string
}

export interface ProfilePayload {
  email: string
  first_name: string
  last_name: string
}

export interface PasswordPayload {
  current_password: string
  new_password: string
  new_password_confirm: string
}

