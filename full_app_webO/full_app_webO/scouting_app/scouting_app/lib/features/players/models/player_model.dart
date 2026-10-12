class Player {
  final int?   id;
  final String fullName;
  final int    age;
  final String gender;
  final String dominantFoot;
  final double? heightCm;
  final double? weightKg;
  final String village;
  final String district;
  final String state;
  final String experienceLevel;
  final String? createdAt;

  Player({
    this.id,
    required this.fullName,
    required this.age,
    required this.gender,
    required this.dominantFoot,
    this.heightCm,
    this.weightKg,
    required this.village,
    required this.district,
    this.state = 'Andhra Pradesh',
    required this.experienceLevel,
    this.createdAt,
  });

  factory Player.fromJson(Map<String, dynamic> json) => Player(
    id:              json['id'],
    fullName:        json['full_name'] ?? '',
    age:             json['age'] ?? 0,
    gender:          json['gender'] ?? 'M',
    dominantFoot:    json['dominant_foot'] ?? 'right',
    heightCm:        json['height_cm']?.toDouble(),
    weightKg:        json['weight_kg']?.toDouble(),
    village:         json['village'] ?? '',
    district:        json['district'] ?? '',
    state:           json['state'] ?? 'Andhra Pradesh',
    experienceLevel: json['experience_level'] ?? 'none',
    createdAt:       json['created_at'],
  );

  Map<String, dynamic> toJson() => {
    'full_name'        : fullName,
    'age'              : age,
    'gender'           : gender,
    'dominant_foot'    : dominantFoot,
    'height_cm'        : heightCm,
    'weight_kg'        : weightKg,
    'village'          : village,
    'district'         : district,
    'state'            : state,
    'experience_level' : experienceLevel,
  };

  String get displayName => fullName;
  String get locationStr => '$village, $district';
  String get genderLabel => gender == 'M' ? 'Male' : gender == 'F' ? 'Female' : 'Other';
}
