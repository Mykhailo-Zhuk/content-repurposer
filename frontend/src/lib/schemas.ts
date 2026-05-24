import { z } from "zod";

export const submitSchema = z.object({
  url: z
    .string()
    .min(1, "Введіть посилання")
    .regex(
      /^https:\/\/(www\.)?(youtube\.com\/watch\?v=[\w-]{11}|youtu\.be\/[\w-]{11})/,
      "Введіть коректне YouTube посилання"
    ),
});

export type SubmitFormValues = z.infer<typeof submitSchema>;
