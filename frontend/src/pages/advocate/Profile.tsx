import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { advocateApi } from '../../services/api';
import { ArrowLeft, Save } from 'lucide-react';

const SPECIALIZATIONS = [
  'civil',
  'matrimonial',
  'criminal',
  'property',
  'constitutional',
  'conveyancing',
];

const STATES = [
  'Delhi',
  'Maharashtra',
  'Karnataka',
  'Tamil Nadu',
  'Uttar Pradesh',
  'West Bengal',
  'Kerala',
  'Rajasthan',
  'Punjab',
  'Haryana',
  'Telangana',
  'Madhya Pradesh',
];

export default function AdvocateProfile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isNewProfile, setIsNewProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    enrollment_number: '',
    enrollment_year: '',
    bar_council: '',
    states: [] as string[],
    districts: '',
    home_court: '',
    primary_specializations: [] as string[],
    experience_years: '',
    fee_category: 'standard',
    consultation_fee: '',
    languages: '',
    office_address: '',
    is_available: true,
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const response = await advocateApi.getProfile();
      const profile = response.data;
      setFormData({
        enrollment_number: profile.enrollment_number || '',
        enrollment_year: profile.enrollment_year?.toString() || '',
        bar_council: profile.bar_council || '',
        states: profile.states || [],
        districts: profile.districts?.join(', ') || '',
        home_court: profile.home_court || '',
        primary_specializations: profile.primary_specializations || [],
        experience_years: profile.experience_years?.toString() || '',
        fee_category: profile.fee_category || 'standard',
        consultation_fee: profile.consultation_fee?.toString() || '',
        languages: profile.languages?.join(', ') || '',
        office_address: profile.office_address || '',
        is_available: profile.is_available ?? true,
      });
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } };
      if (error.response?.status === 404) {
        setIsNewProfile(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData({ ...formData, [name]: checked });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleMultiSelect = (name: string, value: string) => {
    const currentValues = formData[name as keyof typeof formData] as string[];
    const newValues = currentValues.includes(value)
      ? currentValues.filter((v) => v !== value)
      : [...currentValues, value];
    setFormData({ ...formData, [name]: newValues });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    const profileData = {
      enrollment_number: formData.enrollment_number,
      enrollment_year: formData.enrollment_year ? parseInt(formData.enrollment_year) : null,
      bar_council: formData.bar_council,
      states: formData.states,
      districts: formData.districts.split(',').map((d) => d.trim()).filter(Boolean),
      home_court: formData.home_court,
      primary_specializations: formData.primary_specializations,
      experience_years: formData.experience_years ? parseInt(formData.experience_years) : 0,
      fee_category: formData.fee_category,
      consultation_fee: formData.consultation_fee ? parseFloat(formData.consultation_fee) : null,
      languages: formData.languages.split(',').map((l) => l.trim()).filter(Boolean),
      office_address: formData.office_address,
      is_available: formData.is_available,
    };

    try {
      if (isNewProfile) {
        await advocateApi.createProfile(profileData);
        setSuccess('Profile created successfully!');
        setIsNewProfile(false);
      } else {
        await advocateApi.updateProfile(profileData);
        setSuccess('Profile updated successfully!');
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center">
          <button
            onClick={() => navigate('/advocate')}
            className="p-2 hover:bg-gray-100 rounded-full mr-4"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="text-xl font-semibold">
            {isNewProfile ? 'Complete Your Profile' : 'My Profile'}
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Enrollment Number *
              </label>
              <input
                type="text"
                name="enrollment_number"
                value={formData.enrollment_number}
                onChange={handleChange}
                required
                disabled={!isNewProfile}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Year of Enrollment
              </label>
              <input
                type="number"
                name="enrollment_year"
                value={formData.enrollment_year}
                onChange={handleChange}
                min="1950"
                max={new Date().getFullYear()}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bar Council
              </label>
              <input
                type="text"
                name="bar_council"
                value={formData.bar_council}
                onChange={handleChange}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Years of Experience
              </label>
              <input
                type="number"
                name="experience_years"
                value={formData.experience_years}
                onChange={handleChange}
                min="0"
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          {/* States */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Practicing States
            </label>
            <div className="flex flex-wrap gap-2">
              {STATES.map((state) => (
                <button
                  key={state}
                  type="button"
                  onClick={() => handleMultiSelect('states', state)}
                  className={`px-3 py-1 rounded-full text-sm ${
                    formData.states.includes(state)
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {state}
                </button>
              ))}
            </div>
          </div>

          {/* Specializations */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Specializations
            </label>
            <div className="flex flex-wrap gap-2">
              {SPECIALIZATIONS.map((spec) => (
                <button
                  key={spec}
                  type="button"
                  onClick={() => handleMultiSelect('primary_specializations', spec)}
                  className={`px-3 py-1 rounded-full text-sm capitalize ${
                    formData.primary_specializations.includes(spec)
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {spec}
                </button>
              ))}
            </div>
          </div>

          {/* Other fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Home Court
              </label>
              <input
                type="text"
                name="home_court"
                value={formData.home_court}
                onChange={handleChange}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Districts (comma-separated)
              </label>
              <input
                type="text"
                name="districts"
                value={formData.districts}
                onChange={handleChange}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fee Category
              </label>
              <select
                name="fee_category"
                value={formData.fee_category}
                onChange={handleChange}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="premium">Premium</option>
                <option value="standard">Standard</option>
                <option value="affordable">Affordable</option>
                <option value="pro_bono">Pro Bono</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Consultation Fee (₹)
              </label>
              <input
                type="number"
                name="consultation_fee"
                value={formData.consultation_fee}
                onChange={handleChange}
                min="0"
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Languages (comma-separated)
              </label>
              <input
                type="text"
                name="languages"
                value={formData.languages}
                onChange={handleChange}
                placeholder="Hindi, English, Marathi"
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Office Address
              </label>
              <textarea
                name="office_address"
                value={formData.office_address}
                onChange={handleChange}
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          {/* Availability */}
          <div className="flex items-center">
            <input
              type="checkbox"
              name="is_available"
              checked={formData.is_available}
              onChange={handleChange}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label className="ml-2 text-sm text-gray-700">
              Available for new cases
            </label>
          </div>

          {/* Submit */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center space-x-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              <span>{saving ? 'Saving...' : 'Save Profile'}</span>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
