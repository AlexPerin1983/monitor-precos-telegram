import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://whbhxexafjdfumcondmi.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndoYmh4ZXhhZmpkZnVtY29uZG1pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAxMjgxNTgsImV4cCI6MjA4NTcwNDE1OH0.vpo0ntHufGI0_8aTgwi5f3Zwq4YoqRVTkC1DY52umCY'

export const supabase = createClient(supabaseUrl, supabaseKey)
