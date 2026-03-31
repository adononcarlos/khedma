// Avis d'utilisateurs (données de démonstration).
// Chaque avis est rédigé dans sa propre langue et s'affiche tel quel, quelle que soit la langue de l'interface.
// Les dates ne sont pas figées : `at` place l'avis entre le lancement (START) et aujourd'hui,
// ce qui garde un fil d'avis régulier et récent.

export type ReviewProfile = "seeker" | "student" | "pro";
export type ReviewLang = "fr" | "ar" | "en";

export type Review = {
  id: number;
  name: string;
  role: string; // dans la langue de l'avis
  profile: ReviewProfile;
  lang: ReviewLang;
  rating: 4 | 5;
  at: number; // 0 = lancement, 1 = aujourd'hui
  text: string;
};

const START = Date.UTC(2026, 2, 2); // 2 mars 2026
const DAY = 86_400_000;

function reviewDate(r: Review, now: number): Date {
  const span = Math.max(0, now - START);
  return new Date(START + Math.floor((r.at * span) / DAY) * DAY);
}

// Avis datés au moment de la requête, du plus récent au plus ancien
export function datedReviews(list: Review[] = REVIEWS, now = Date.now()) {
  return list.map((r) => ({ r, date: reviewDate(r, now) })).sort((a, b) => b.date.getTime() - a.date.getTime());
}

export const REVIEWS: Review[] = [
  { id: 1, name: "Salma B.", role: "Technicienne de maintenance, Kénitra", profile: "seeker", lang: "fr", rating: 5, at: 0.03,
    text: "J'ai déposé mon CV un dimanche soir ; le lundi, j'avais une liste d'offres classées avec un score. Le CV généré pour un poste à Kénitra m'a valu un entretien, puis un CDI. Merci Khedma !" },
  { id: 2, name: "حمزة أ.", role: "باحث عن عمل، فاس", profile: "seeker", lang: "ar", rating: 5, at: 0.06,
    text: "لم أكن أعلم أن عقد الإدماج أصبح متاحاً حتى لغير الحاصلين على شهادة بفضل القانون 51.25. شرحت لي خدمة ذلك ووجهتني إلى عروض تناسبني. شكراً جزيلاً." },
  { id: 3, name: "Amine S.", role: "Software engineer, Rabat", profile: "seeker", lang: "en", rating: 5, at: 0.09,
    text: "I applied to several English-language offers and Khedma produced my CV and cover letter in English automatically. Clean, fast and genuinely useful." },
  { id: 4, name: "Aminata D.", role: "Étudiante sénégalaise, master en finance, Casablanca", profile: "student", lang: "fr", rating: 5, at: 0.12,
    text: "En tant qu'étudiante étrangère, je ne savais pas par où commencer. Khedma m'a montré les stages ouverts dans ma ville et m'a aidée à écrire une lettre adaptée au marché marocain. Stage décroché !" },
  { id: 5, name: "Youssef E.", role: "Comptable junior, Casablanca", profile: "seeker", lang: "fr", rating: 5, at: 0.15,
    text: "Avant, je passais mes soirées sur cinq sites différents. Ici tout est au même endroit, avec des filtres qui marchent vraiment. Trois entretiens en deux semaines." },
  { id: 6, name: "فاطمة الزهراء م.", role: "ممرضة، مراكش", profile: "seeker", lang: "ar", rating: 5, at: 0.18,
    text: "منصة رائعة وسهلة الاستعمال. وجدت عروضاً في القطاع الصحي لم أكن أراها في المواقع الأخرى، وكانت سيرتي الذاتية جاهزة في دقيقة واحدة." },
  { id: 7, name: "Chinedu O.", role: "Nigerian MBA student, Casablanca", profile: "student", lang: "en", rating: 5, at: 0.21,
    text: "Offers are translated, so I could understand French job ads before applying. That made all the difference for me as an international student." },
  { id: 8, name: "Nadia L.", role: "Assistante administrative, Rabat", profile: "seeker", lang: "fr", rating: 4, at: 0.24,
    text: "Après dix ans au même poste, je ne savais plus rédiger une lettre. Celle proposée par Khedma était sobre et juste ; je l'ai à peine retouchée." },
  { id: 9, name: "Leila K.", role: "Conseillère emploi, Casablanca", profile: "pro", lang: "fr", rating: 5, at: 0.27,
    text: "Le portefeuille classé par priorité change mon quotidien : je vois tout de suite les candidats à relancer, et les offres suggérées me font gagner des heures." },
  { id: 10, name: "أحمد سالم", role: "طالب موريتاني في الهندسة، الرباط", profile: "student", lang: "ar", rating: 5, at: 0.3,
    text: "كطالب أجنبي، كنت أجد صعوبة في فهم سوق الشغل المغربي. سهّلت عليّ المنصة كل شيء، وحصلت على تدريب في شركة بالدار البيضاء." },
  { id: 11, name: "Mehdi T.", role: "Analyste data, Casablanca", profile: "seeker", lang: "fr", rating: 5, at: 0.33,
    text: "Ce que j'apprécie, c'est que le score est expliqué : je vois mes atouts et ce qui me manque. Pour une offre en anglais, le CV est sorti directement en anglais." },
  { id: 12, name: "Grace M.", role: "Kenyan student in international relations, Rabat", profile: "student", lang: "en", rating: 5, at: 0.36,
    text: "It helped me understand the Moroccan job market in a week, and I landed an internship with an NGO. Keep up the great work!" },
  { id: 13, name: "عمر ك.", role: "سائق ومسؤول توصيل، طنجة", profile: "seeker", lang: "ar", rating: 4, at: 0.39,
    text: "الواجهة بالعربية واضحة جداً، وهذا مهم بالنسبة لي. حصلت على مقابلتين خلال أسبوع واحد." },
  { id: 14, name: "Koffi A.", role: "Étudiant ivoirien en génie industriel, Rabat", profile: "student", lang: "fr", rating: 5, at: 0.42,
    text: "Les offres sont bien triées et le matching tient compte de mon vrai profil, pas seulement des mots-clés. Félicitations pour ce projet." },
  { id: 15, name: "Ilham B.", role: "Reconversion vers la relation client, Marrakech", profile: "seeker", lang: "fr", rating: 5, at: 0.45,
    text: "Je venais de l'hôtellerie et je voulais changer de voie. La rubrique « Compétences à développer » m'a orientée vers une formation gratuite de l'ANAPEC. Aujourd'hui, je suis conseillère clientèle." },
  { id: 16, name: "خديجة ر.", role: "مستشارة مبيعات، أكادير", profile: "seeker", lang: "ar", rating: 5, at: 0.48,
    text: "أعجبني قسم «مهارات يجب تطويرها»، فقد دلّني على تكوين مجاني عبر الإنترنت. أنصح بالمنصة كل الباحثين عن عمل." },
  { id: 17, name: "Sara El M.", role: "HR specialist, Casablanca", profile: "seeker", lang: "en", rating: 5, at: 0.51,
    text: "The explanation behind each match score is what sold me: I know exactly which skills to highlight. Congratulations to the team!" },
  { id: 18, name: "Mariam T.", role: "Étudiante malienne en hôtellerie, Marrakech", profile: "student", lang: "fr", rating: 4, at: 0.54,
    text: "Très utile pour trouver des stages saisonniers. J'aimerais encore plus d'offres dans le tourisme, mais c'est déjà un vrai gain de temps." },
  { id: 19, name: "رشيد و.", role: "تقني في البناء، وجدة", profile: "seeker", lang: "ar", rating: 5, at: 0.57,
    text: "بعد أشهر من البحث، وجدت عقد عمل في مدينتي. شكراً لفريق خدمة على هذا العمل المتقن." },
  { id: 20, name: "Karim J.", role: "Responsable RH d'une PME, Casablanca", profile: "pro", lang: "fr", rating: 4, at: 0.6,
    text: "Les candidatures reçues via Khedma sont mieux ciblées : les CV mettent en avant ce que nous demandons. Belle initiative." },
  { id: 21, name: "Kwame B.", role: "Ghanaian student in tourism, Agadir", profile: "student", lang: "en", rating: 4, at: 0.63,
    text: "Very handy for seasonal internships along the coast. A mobile app would be the cherry on top." },
  { id: 22, name: "Jean-Baptiste N.", role: "Étudiant camerounais en informatique, Fès", profile: "student", lang: "fr", rating: 5, at: 0.66,
    text: "Le CV d'une page généré par l'IA est propre et lisible par les logiciels de recrutement. Mon premier entretien au Maroc, je le dois à Khedma." },
  { id: 23, name: "زينب ف.", role: "خريجة جديدة في الموارد البشرية، الرباط", profile: "seeker", lang: "ar", rating: 5, at: 0.69,
    text: "مبادرة تستحق التشجيع. رسالة التحفيز التي أعدّتها المنصة كانت مقنعة ومكتوبة بلغة سليمة." },
  { id: 24, name: "Soukaina H.", role: "Jeune diplômée en marketing, Tétouan", profile: "seeker", lang: "fr", rating: 5, at: 0.72,
    text: "Bravo à toute l'équipe ! Une plateforme marocaine aussi claire, en trois langues et avec un mode sombre, c'est une première pour moi." },
  { id: 25, name: "Aisha B.", role: "Sudanese computer science student, Casablanca", profile: "student", lang: "en", rating: 5, at: 0.75,
    text: "Being able to switch between Arabic and English is wonderful, and the one-page CV looks truly professional." },
  { id: 26, name: "محمد ب.", role: "مستشار في التشغيل، طنجة", profile: "pro", lang: "ar", rating: 5, at: 0.78,
    text: "الاقتراحات التي يقدمها الذكاء الاصطناعي لكل مرشح دقيقة، وتوفر علينا الكثير من الوقت في المتابعة." },
  { id: 27, name: "Fatou S.", role: "Étudiante guinéenne en logistique, Tanger", profile: "student", lang: "fr", rating: 5, at: 0.81,
    text: "J'ai trouvé un stage de fin d'études dans la zone de Tanger Med en moins d'un mois. Merci et bon courage à l'équipe !" },
  { id: 28, name: "Youssef A.", role: "Back in Morocco after six years abroad, Tangier", profile: "seeker", lang: "en", rating: 5, at: 0.84,
    text: "Coming home after years in Europe, I needed a quick overview of the market. Khedma gave me exactly that, plus tailored applications." },
  { id: 29, name: "عبد الإله ز.", role: "تقني فلاحي، بني ملال", profile: "seeker", lang: "ar", rating: 5, at: 0.86,
    text: "أخيراً منصة مغربية تجمع كل العروض في مكان واحد، حتى في الفلاحة. بالتوفيق وإلى الأمام." },
  { id: 30, name: "Chaimae E.", role: "Reprise d'activité, Salé", profile: "seeker", lang: "fr", rating: 4, at: 0.88,
    text: "Après une pause de quatre ans, j'avais peur de reprendre. Les offres IDMAJ proposées m'ont redonné confiance. Continuez comme ça !" },
  { id: 31, name: "Emmanuel K.", role: "Congolese engineering student, Rabat", profile: "student", lang: "en", rating: 5, at: 0.9,
    text: "I recommend Khedma to every international student in Morocco: honest scores, relevant offers, zero hassle." },
  { id: 32, name: "يارا ح.", role: "طالبة أردنية في الصيدلة، الرباط", profile: "student", lang: "ar", rating: 5, at: 0.92,
    text: "تجربة موفقة جداً: عروض واضحة، وتقييم يشرح مدى توافق ملفي مع كل عرض. شكراً لكم." },
  { id: 33, name: "Brice M.", role: "Étudiant gabonais en commerce international, Kénitra", profile: "student", lang: "fr", rating: 5, at: 0.94,
    text: "Interface agréable, offres à jour, et les conseils de formation sont un vrai plus. Je la recommande à tous les étudiants internationaux." },
  { id: 34, name: "Laura G.", role: "Talent acquisition, Tangier free zone", profile: "pro", lang: "en", rating: 4, at: 0.96,
    text: "Candidates coming from Khedma send documents that actually match our job descriptions. Impressive work for a young platform." },
  { id: 35, name: "سعيد ل.", role: "عامل في الصناعة، القنيطرة", profile: "seeker", lang: "ar", rating: 4, at: 0.98,
    text: "خدمة ممتازة، وأتمنى أن تضيفوا المزيد من العروض في المدن الصغيرة. شكراً على المجهود." },
  { id: 36, name: "Hicham D.", role: "Technicien réseaux, Meknès", profile: "seeker", lang: "fr", rating: 5, at: 0.995,
    text: "Simple, rapide, efficace. J'ai recommandé Khedma à tout mon groupe de l'ISTA." },
];

export function reviewStats(list: Review[] = REVIEWS) {
  const n = list.length;
  const avg = n ? list.reduce((s, r) => s + r.rating, 0) / n : 0;
  const byStars = [5, 4, 3, 2, 1].map((s) => ({ stars: s, count: list.filter((r) => r.rating === s).length }));
  const fiveStars = n ? byStars[0].count / n : 0;
  return { n, avg, fiveStars, byStars };
}
